import datetime
import json
import uuid
from zoneinfo import ZoneInfo

import functions_framework
import pandas as pd
import telemetrics
from flask import Request, abort
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from infra import auth, authenticated_user_id  # type: ignore
from infra.alpaca_action import get_available_cash, get_model_portfolio_by_name
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Missions, Runs
from infra.data.users import User
from infra.logger import log_error
from infra.plaid_actions import get_bank_account_balance
from infra.proxies.alpaca import alpaca_proxy  # type: ignore
from infra.stytch_actions import get_from_user_vault


def save_new_mission(
    user_id: str,
    mission_name: str,
    strategy: str,
    initial_amount: str | None,
    weekly_topup: str | None,
) -> str | None:
    if Missions.exists_by_name(user_id, mission_name):
        log_error(
            "save_new_mission()",
            f"{user_id} already has mission {mission_name}",
        )
        return None

    return Missions.add(
        user_id, mission_name, strategy, initial_amount, weekly_topup
    )


def create_run(
    user_id: str, alpaca_account_id: str, model_portfolio: dict
) -> str | None:
    """rebalance user account, to bring it to same allocations as in the model portfolio"""

    cash = get_available_cash(alpaca_account_id)
    if not cash:
        log_error(
            "create_run()", "account can't be used for trading at the moment"
        )
        return None
    elif cash < 1.0:
        log_error(
            "create_run()", f"account balance {cash} too low for trading"
        )
        return None

    # TODO: Do we need anything except weights?
    rebalance_payload: dict = {
        "account_id": alpaca_account_id,
        "type": "full_rebalance",
        "weights": model_portfolio["weights"],
    }

    r = alpaca_proxy(
        method="POST",
        url="/v1/beta/rebalancing/runs",
        payload=rebalance_payload,
        args=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "create_run",
            f"run failed status code {r.status_code} and {r.text}",
        )

        return "reschedule" if r.status_code == 422 else None

    run_payload = r.json()
    telemetrics.run_status(run_payload["status"])
    telemetrics.mission_amount(int(cash))

    return run_payload["id"]


def calculate_seconds_from_now() -> int | None:
    EDT = ZoneInfo("US/Eastern")
    now_in_nyc = datetime.datetime.now(EDT)
    today_in_nyc = now_in_nyc.date()

    args = {
        "start": today_in_nyc,
        "end": today_in_nyc + datetime.timedelta(days=7),
    }
    r = alpaca_proxy(
        method="GET",
        url="/v1/calendar",
        args=args,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        return None

    calendars = r.json()
    first_trading_calendar = calendars[0]

    # Is today a trading day?
    if first_trading_calendar["date"] == str(today_in_nyc):
        return _extracted_from_calculate_seconds_from_now_27(
            first_trading_calendar, EDT, now_in_nyc, calendars
        )
    next_market_open = datetime.datetime.combine(
        datetime.datetime.strptime(
            first_trading_calendar["date"], "%Y-%m-%d"
        ).date(),
        datetime.datetime.strptime(
            first_trading_calendar["open"], "%H:%M"
        ).time(),
        EDT,
    )

    return int((next_market_open - now_in_nyc).total_seconds())


# TODO Rename this here and in `calculate_seconds_from_now`
def _extracted_from_calculate_seconds_from_now_27(
    first_trading_calendar, EDT, now_in_nyc, calendars
):
    market_open = datetime.datetime.combine(
        datetime.datetime.strptime(
            first_trading_calendar["date"], "%Y-%m-%d"
        ).date(),
        datetime.datetime.strptime(
            first_trading_calendar["open"], "%H:%M"
        ).time(),
        EDT,
    )
    market_close = datetime.datetime.combine(
        datetime.datetime.strptime(
            first_trading_calendar["date"], "%Y-%m-%d"
        ).date(),
        datetime.datetime.strptime(
            first_trading_calendar["close"], "%H:%M"
        ).time(),
        EDT,
    )
    if now_in_nyc < market_open:
        return int((market_open - now_in_nyc).total_seconds())
    elif now_in_nyc < market_close:
        return 60 * 5

    next_trading_day = calendars[1]
    next_market_open = datetime.datetime.combine(
        datetime.datetime.strptime(
            next_trading_day["date"], "%Y-%m-%d"
        ).date(),
        datetime.datetime.strptime(next_trading_day["open"], "%H:%M").time(),
        EDT,
    )

    return int((next_market_open - now_in_nyc).total_seconds())


def set_task(
    client: tasks_v2.CloudTasksClient, task: tasks_v2.Task
) -> tuple[str, int]:
    if not (second_from_now := calculate_seconds_from_now()):
        return ("failed to calculate 'set_task' schedule", 400)

    # Convert "seconds from now" to an absolute Protobuf Timestamp
    second_from_now = int(second_from_now)  # type : ignore
    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=second_from_now)
    )
    task.schedule_time = timestamp

    # Use the client to send a CreateTaskRequest.
    _ = client.create_task(
        tasks_v2.CreateTaskRequest(
            # The queue to add the task to
            parent=client.queue_path(project_id, location, rebalance_queue),  # type: ignore
            # The task itself
            task=task,
        )
    )
    return ("scheduled", 201)


def reschedule_run(request):
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url="https://api.nine30.com/v1/missions",
            headers=request.headers,
            body=json.dumps(request.json).encode(),
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task)


def handle_create_mission(request: Request):
    payload = request.get_json() if request.is_json else None

    if (
        not payload
        or not (name := payload.get("name"))
        or not (strategy := payload.get("strategy"))
    ):
        if payload:
            log_error("handle_post", f"payload={payload}")
        return ("Missing or invalid payload", 400)

    initial_amount = payload.get("initialAmount")
    weekly_topup = payload.get("weeklyTopup")

    user_id = authenticated_user_id.get()  # type: ignore

    if not (model_portfolio := get_model_portfolio_by_name(strategy)):
        return (f"model portfolio '{strategy}' not found", 400)

    print(
        f"Located portfolio id {model_portfolio['id']} for strategy name {strategy}"
    )

    mission_id = save_new_mission(
        user_id=user_id,
        mission_name=name,
        strategy=strategy,
        initial_amount=initial_amount,
        weekly_topup=weekly_topup,
    )

    if not mission_id:
        abort(400)

    User.update(user_id=user_id, payload={"mission": True})
    return ({"mission_id": mission_id}, 202)


def reschedule_verify(
    request: Request,
    user_id: str,
    run_id: str,
) -> tuple[str, int]:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PATCH,
            url=f"https://api.nine30.com/v1/runs/{run_id}?userId={user_id}",
            headers=request.headers,
            body=json.dumps(request.json).encode(),
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task)


def handle_validate(request: Request) -> tuple[str, int]:
    # validate
    if not (run_id := request.args.get("runId")):
        log_error("handle_validate()", "missing runId")
        abort(202)

    if not (user_id := request.args.get("userId")):
        log_error("handle_validate()", "missing userId")
        abort(202)

    # TODO: move to alpaca_actions
    r = alpaca_proxy(
        method="GET",
        url=f"/v1/rebalancing/runs/{run_id}",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error("handle_get()", f"failed to load run {run_id}: {r.text}")
        return (f"run id {run_id} not found", 400)

    payload = r.json()
    status = payload["status"]
    telemetrics.run_status(status)
    print(f"validating run {run_id} with status={status}")

    if status in {"COMPLETED_SUCCESS", "COMPLETED_ADJUSTED"}:
        Runs.update(user_id=user_id, run_id=run_id, details=payload)
        return (f"{status}", 200)
    elif status in {"IN_PROGRESS", "QUEUED"}:
        return reschedule_verify(request, user_id, run_id)

    log_error("handle_validate()", f"unhandled status {status} in {payload}")
    abort(202)


def _calc_initial_amounts(balance: float) -> tuple[int, int]:
    """Calculate initial investment amounts based on account balance"""

    initial_amount = int(balance * 0.1)
    weekly_topup = int(balance * 0.025)
    return initial_amount, weekly_topup


# TODO: use infra
def handle_mission_suggestion(request):
    if not (user_id := authenticated_user_id.get()):
        log_error("handle_mission_suggestion()", "user not specified")
        abort(403)

    if not (
        plaid_access_token := get_from_user_vault(
            user_id, "plaid_access_token"
        )
    ):
        log_error("handle_mission_suggestion()", "not linked to Plaid")
        abort(400)

    if not (balance := get_bank_account_balance(user_id, plaid_access_token)):
        log_error(
            "handle_mission_suggestion()",
            f"could not get balance for {user_id}",
        )
        abort(400)

    initial_investment, weekly_topup = _calc_initial_amounts(balance)
    bins = int(request.args.get("bins") or 30)

    num_years_to_calc = 30
    annual_interest = 0.1
    weekly_interest = annual_interest / 52
    num_weeks = 52 * num_years_to_calc

    deposit = [weekly_topup] * num_weeks
    deposit[0] += initial_investment
    rate = [weekly_interest] * num_weeks

    df = pd.DataFrame({"deposit": deposit, "rate": rate})
    df["total"] = (
        df["deposit"] * df["rate"].shift().add(1).cumprod().fillna(1)
    ).cumsum()
    df["year"] = df.index // (52 * num_years_to_calc / bins)

    new_df = pd.DataFrame(
        {
            "deposit": df.groupby("year").sum()["deposit"].cumsum(),
            "amount": df.groupby("year").last()["total"],
        }
    ).round(1)

    return (
        {
            "strategy": "protector",
            "initialAmount": initial_investment,
            "topupAmount": weekly_topup,
            "frequency": "weekly",
            "forecast": new_df.values.tolist(),
        },
        200,
    )


@functions_framework.http
@auth
def missions(request):
    """Implement /v1/missions end points"""

    if request.method == "GET":
        return handle_mission_suggestion(request)
    if request.method == "POST":
        return handle_create_mission(request)
    if request.method == "PATCH":
        return handle_validate(request)

    return (f"{request.method} not yet implemented", 405)
