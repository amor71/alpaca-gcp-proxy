import datetime
import uuid
from zoneinfo import ZoneInfo

import functions_framework
from flask import Request, abort
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from infra.alpaca_action import get_available_cash, get_model_portfolio_by_name
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Missions, Runs
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore
from infra.stytch_actions import get_alpaca_account_id


def save_run(
    user_id: str,
    run_id: str,
    mission_name: str,
    strategy: str,
) -> None:
    Runs.add(user_id, run_id, mission_name, strategy)


def calculate_seconds_from_now() -> int | None:
    EDT = ZoneInfo("US/Eastern")
    now_in_nyc = datetime.datetime.now(EDT)
    today_in_nyc = now_in_nyc.date()

    # TODO: move to infra
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
    client: tasks_v2.CloudTasksClient, task: tasks_v2.Task, offset: int = 0
) -> tuple[str, int]:
    if not (second_from_now := calculate_seconds_from_now()):
        return ("failed to calculate 'set_task' schedule", 400)

    # Convert "seconds from now" to an absolute Protobuf Timestamp
    second_from_now = int(second_from_now) + offset  # type : ignore
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


def reschedule_run(user_id, request):
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"https://api.nine30.com/v1/missions/rebalance/{user_id}",
            headers=request.headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task)


# TODO: move to infra and consolidate w/ mission end-point
def create_run(alpaca_account_id: str, model_portfolio: dict) -> str | None:
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

    # TODO: move to infra
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
    print(f"created run with id {run_payload.get('id')}")
    return run_payload["id"]


def handle_create_rebalance(request: Request):
    print("handle_create_rebalance")
    print(request)
    # validate API
    if not (user_id := request.args.get("userId")):
        log_error("handle_users_topup()", "missing user_id")
        abort(400)

    print(f"loading missions for user_id {user_id}")
    missions = Missions(user_id)

    print("missions:", missions)
    for mission in missions:
        strategy = mission.get("strategy")
        if not (model_portfolio := get_model_portfolio_by_name(strategy)):
            log_error(
                "handle_create_rebalance()",
                f"model portfolio '{strategy}' not found",
            )
            return ("invalid strategy", 202)

        if not (alpaca_account_id := get_alpaca_account_id(user_id)):
            log_error(
                "handle_create_rebalance()",
                f"user_id {user_id} does not have alpaca_account_id (yet)",
            )
            return ("invalid_user", 202)

        print(f"creating run for {alpaca_account_id} with {model_portfolio}")
        if not (run_id := create_run(alpaca_account_id, model_portfolio)):
            return ("failed run", 201)

        if run_id == "reschedule":
            return reschedule_run(user_id, request)

        save_run(
            user_id=user_id,
            run_id=run_id,
            mission_name=mission.get("name"),
            strategy=mission.get("strategy"),
        )

        schedule_verify_run(user_id, run_id, request)

    return ("OK", 200)


def schedule_verify_run(
    user_id: str,
    run_id: str,
    request: Request,
) -> tuple[str, int]:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PATCH,
            url=f"https://api.nine30.com/v1/missions/validate/{run_id}?userId={user_id}",
            headers=request.headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task, 60 * 5)


@functions_framework.http
def rebalance(request):
    """Implement /v1/missions/rebalance/{userId} end points"""

    print("here!", request.method)
    if request.method == "POST":
        return handle_create_rebalance(request)

    return (f"{request.method} not yet implemented", 405)
