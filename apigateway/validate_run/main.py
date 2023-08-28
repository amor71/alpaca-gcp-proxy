import datetime
import uuid
from zoneinfo import ZoneInfo

import functions_framework
from flask import Request, abort
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Runs
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore


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


def schedule_verify_run(
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
            url=f"https://api.nine30.com/v1/missions/validate/{run_id}",
            headers=request.headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task, 60 * 5)


def handle_validate_run(request: Request):
    # validate API
    if not (run_id := request.args.get("runId")):
        log_error("handle_validate_run()", "missing runId")
        abort(400)
    if not (user_id := request.args.get("userId")):
        log_error("handle_validate_run()", "missing userId")
        abort(400)

    r = alpaca_proxy(
        method="GET",
        url=f"/v1/rebalancing/runs/{run_id}",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "handle_validate_run()", f"failed to load run {run_id}: {r.text}"
        )
        abort(400)

    payload = r.json()
    status = payload["status"]
    print(f"validating run {run_id} with {status} in {payload}")

    # TODO: handle case of failed orders!
    if status in {"COMPLETED_SUCCESS", "COMPLETED_ADJUSTED"}:
        Runs.update(user_id=user_id, run_id=run_id, details=payload)
        return (f"{status}", 200)
    elif status in {"IN_PROGRESS", "QUEUED"}:
        return schedule_verify_run(run_id, request)

    log_error("handle_validate_run()", f"unknown status {status} in {payload}")
    return ("OK", 202)


@functions_framework.http
def validate_run(request):
    """Implement /v1/missions/validate/{runId} end points"""

    if request.method == "PATCH":
        return handle_validate_run(request)

    return (f"{request.method} not yet implemented", 405)
