import datetime
import json
import time
import uuid

import functions_framework
import pytz
from google.cloud import firestore  # type: ignore
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from infra import auth, authenticated_user_id  # type: ignore
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore


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

    print(f"loaded document:{doc}")
    if not (alpaca_account_id := doc.get("alpaca_account_id")):
        log_error(
            "load_account_id",
            f"{user_id} does not have 'alpaca_account_id' property",
        )
        return None

    return alpaca_account_id


def save_new_mission(
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

    run_doc_def = doc_ref.collection("runs").document()
    run_data = {"run_id": run_id, "created": created}
    status = run_doc_def.set(run_data)

    print("document update status=", status)
    return doc_ref.id, created


def create_run(user_id: str, model_portfolio: dict) -> str | None:
    """rebalance user account, to bring it to same allocations as in the model portfolio"""

    if not (user_account_id := load_account_id(user_id)):
        return None

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
    return run_payload["id"]


def calculate_seconds_from_now() -> int | None:
    now_in_nyc = datetime.datetime.now(pytz.timezone("America/New_York"))
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
        market_open = datetime.datetime.combine(
            datetime.datetime.strptime(
                first_trading_calendar["date"], "'%Y-%m-%d'"
            ).date(),
            datetime.datetime.strptime(
                first_trading_calendar["open"], "%H:%M"
            ).time(),
            pytz.timezone("America/New_York"),
        )
        market_close = datetime.datetime.combine(
            datetime.datetime.strptime(
                first_trading_calendar["date"], "%Y-%m-%d"
            ).date(),
            datetime.datetime.strptime(
                first_trading_calendar["open"], "%H:%M"
            ).time(),
            pytz.timezone("America/New_York"),
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
            datetime.datetime.strptime(
                next_trading_day["open"], "%H:%M"
            ).time(),
            pytz.timezone("America/New_York"),
        )

        return int((next_market_open - now_in_nyc).total_seconds())

    next_market_open = datetime.datetime.combine(
        datetime.datetime.strptime(
            first_trading_calendar["date"], "%Y-%m-%d"
        ).date(),
        datetime.datetime.strptime(
            first_trading_calendar["open"], "%H:%M"
        ).time(),
        pytz.timezone("America/New_York"),
    )

    print(
        f"next market open time: {next_market_open}, now in ny: {now_in_nyc}"
    )
    return int((next_market_open - now_in_nyc).total_seconds())


def reschedule_run(request):
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())
    print(
        f"task-id={task_id}, location={location} rebalance_queue={rebalance_queue}"
    )
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
    second_from_now = calculate_seconds_from_now()

    # Convert "seconds from now" to an absolute Protobuf Timestamp
    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=second_from_now)
    )
    task.schedule_time = timestamp

    # Use the client to send a CreateTaskRequest.
    task = client.create_task(
        tasks_v2.CreateTaskRequest(
            # The queue to add the task to
            parent=client.queue_path(project_id, location, rebalance_queue),
            # The task itself
            task=task,
        )
    )

    print(f"created task = {task}")

    return ("scheduled", 201)


def handle_post(request):
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

    mission_id, created = save_new_mission(user_id, name, strategy, run_id)

    # track_run(run_id)

    return ({"id": mission_id, "status": "created", "created": created}, 200)


@functions_framework.http
@auth
def missions(request):
    """Implement /v1/missions"""

    if request.method == "POST":
        return handle_post(request)

    return (f"{request.method} not yet implemented", 405)
