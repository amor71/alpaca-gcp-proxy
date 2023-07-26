import datetime
import json
import time
import uuid
from zoneinfo import ZoneInfo

import functions_framework
from flask import Request
from google.cloud import firestore  # type: ignore
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from infra import auth, authenticated_user_id  # type: ignore
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore

from .alpaca import get_available_cash
from .telemetrics import increment_counter


def get_model_portfolio_by_name(name: str) -> dict | None:
    """Look-up a portfolio by portfolio name"""

    r = alpaca_proxy(
        method="GET",
        url="/v1/beta/rebalancing/portfolios",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        return None

    portfolios = r.json()
    return next(
        (
            portfolio
            for portfolio in portfolios
            if portfolio["name"].lower() == name.lower()
            and portfolio["status"] == "active"
        ),
        None,
    )


def load_account_id(user_id: str) -> str | None:
    """Load account-id from Firestore, based on the user-id"""

    db = firestore.Client()
    doc_ref = db.collection("users").document(user_id)

    if not (doc := doc_ref.get()):
        log_error("load_account_id", f"could not load {user_id} document")
        return None

    if not (alpaca_account_id := doc.get("alpaca_account_id")):
        log_error(
            "load_account_id",
            f"{user_id} does not have 'alpaca_account_id' property",
        )
        return None

    return alpaca_account_id


def save_new_mission_and_run(
    user_id: str, mission_name: str, strategy: str, run_id: str
) -> tuple[str, int]:
    db = firestore.Client()

    created = time.time_ns()
    doc_ref = (
        db.collection("missions")
        .document(user_id)
        .collection("user_missions")
        .document()
    )
    data = {
        "name": mission_name,
        "strategy": strategy,
        "created": created,
    }

    status = doc_ref.set(data)
    print("document update status=", status)

    run_doc_def = db.collection("runs").document(run_id)
    status = run_doc_def.set(data)
    print("document update status=", status)

    return doc_ref.id, created


def create_run(user_id: str, model_portfolio: dict) -> str | None:
    """rebalance user account, to bring it to same allocations as in the model portfolio"""

    if not (user_account_id := load_account_id(user_id)):
        return None

    cash = get_available_cash(user_account_id)
    if not cash or cash < 1.0:
        log_error(
            "create_run", "account can't be used for trading at the moment."
        )
        return None

    print(f"cash={cash}")

    # TODO: Do we need anything except weights?
    rebalance_payload: dict = {
        "account_id": user_account_id,
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
    increment_counter(run_payload["status"])

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
    print(
        f"first_trading_calendar={first_trading_calendar} today_in_nyc={today_in_nyc}"
    )
    # Is today a trading day?

    if first_trading_calendar["date"] == str(today_in_nyc):
        print("its today!")
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

    print(
        f"next market open time: {next_market_open}, now in ny: {now_in_nyc}"
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

    print(
        f"market_open={market_open}, market_close={market_close}, now_in_nyc={now_in_nyc}"
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

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("handle_post", "could not load authenticated user_id")
        return None

    if not (model_portfolio := get_model_portfolio_by_name(strategy)):
        return (f"model portfolio '{strategy}' not found", 400)

    print(
        f"Located portfolio id {model_portfolio['id']} for strategy name {strategy}"
    )

    if not (run_id := create_run(user_id, model_portfolio)):
        return ("could not create rebalance run", 400)

    if run_id == "reschedule":
        return reschedule_run(request)

    print(f"created run with id {run_id}")

    mission_id, created = save_new_mission_and_run(
        user_id, name, strategy, run_id
    )

    _ = reschedule_verify(request=request, run_id=run_id)

    return ({"id": mission_id, "status": "created", "created": created}, 200)


def reschedule_verify(
    request: Request,
    run_id: str,
) -> tuple[str, int]:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PATCH,
            url=f"https://api.nine30.com/v1/runs/{run_id}",
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


def reschedule_run_by_run_id(request: Request, run_id: str) -> tuple[str, int]:
    if not project_id or not location or not rebalance_queue:
        log_error(
            "reschedule_run_by_run_id", "could not load environment variables"
        )
        return ("missing environment variable(s)", 400)

    # load run details
    db = firestore.Client()
    doc = db.collection("runs").document(run_id).get()

    if doc.exists:
        data = doc.to_dict()
    else:
        log_error("reschedule_run_by_run_id", "could not load run {run_id}")
        return ("failed to load previous run details", 400)

    # Create a client.
    client = tasks_v2.CloudTasksClient()
    task_id = str(uuid.uuid4())

    # Construct the task.
    payload = {
        "name": data["name"],
        "strategy": data["strategy"],
    }

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url="https://api.nine30.com/v1/missions",
            headers=request.headers,
            body=json.dumps(payload).encode(),
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task)


def handle_validate(request: Request) -> tuple[str, int]:
    run_id = request.args.get("runId")

    if not run_id:
        return ("missing run-id", 400)

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
    increment_counter(status)
    print(f"validating run {run_id} with status={status}")

    if status in {"COMPLETED_SUCCESS", "COMPLETED_ADJUSTED"}:
        return (f"{status}", 200)
    elif status in {"IN_PROGRESS", "QUEUED"}:
        return reschedule_verify(request, run_id)

    return reschedule_run_by_run_id(request, run_id)


@functions_framework.http
@auth
def missions(request):
    """Implement POST /v1/missions and GET /v1/runs/{run-id}"""

    if request.method == "POST":
        return handle_create_mission(request)
    if request.method == "PATCH":
        return handle_validate(request)

    return (f"{request.method} not yet implemented", 405)
