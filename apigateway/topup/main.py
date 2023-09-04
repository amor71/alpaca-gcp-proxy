import datetime
import json
import uuid

import functions_framework
from flask import abort
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from infra.alpaca_action import (bank_link_ready, get_transfers,
                                 transfer_amount, validate_before_transfer)
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.transfers import Transfer
from infra.infra.data.users import User
from infra.logger import log_error
from infra.stytch_actions import get_alpaca_account_id, get_from_user_vault


def set_task(
    client: tasks_v2.CloudTasksClient,
    task: tasks_v2.Task,
    second_from_now: int = 0,
) -> datetime.datetime:
    run_time = datetime.datetime.now(datetime.timezone.utc)
    if second_from_now:
        # Convert "seconds from now" to an absolute Protobuf Timestamp
        timestamp = timestamp_pb2.Timestamp()
        run_time += datetime.timedelta(seconds=second_from_now)
        timestamp.FromDatetime(run_time)
        task.schedule_time = timestamp
        print(f"set_task() scheduling for {task.schedule_time}")

    # Use the client to send a CreateTaskRequest.
    _ = client.create_task(
        tasks_v2.CreateTaskRequest(
            # The queue to add the task to
            parent=client.queue_path(project_id, location, rebalance_queue),  # type: ignore
            # The task itself
            task=task,
        )
    )
    return run_time


def schedule_transfer_validator(user_id, id, headers):
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.GET,
            url=f"https://api.nine30.com/v1/transfers/{id}?userId={user_id}",
            headers=headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )

    return set_task(client, task, 60 * 60)


def transfer(
    user_id: str,
    alpaca_account_id: str,
    relationship_id: str,
    amount: int,
    headers,
) -> datetime.datetime | None:
    """Initiate a transfer of 'amount' to user's alpaca account"""

    if not validate_before_transfer(alpaca_account_id):
        log_error(
            "transfer()",
            f"{alpaca_account_id} account validation failed, aborting transfer",
        )
        return None

    if not (
        transfer_details := transfer_amount(
            alpaca_account_id, relationship_id, amount
        )
    ):
        return None

    print(f"transfer() result : {transfer_details}")
    transfer = Transfer(user_id=user_id, details=transfer_details)

    return schedule_transfer_validator(user_id, transfer.id, headers)


def weekly_transfer(user_id: str, amount: int, headers) -> datetime.datetime:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())
    payload = {"initialAmount": amount, "weeklyTopup": amount}

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PUT,
            url=f"https://api.nine30.com/v1/users/topup/{user_id}",
            headers=headers,
            body=json.dumps(payload).encode(),
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    weekly_schedule = set_task(client, task, 60 * 60 * 24 * 7)
    User.update(
        user_id=user_id,
        payload={
            "next_payment_schedule": weekly_schedule,
            "next_payment_amount": amount,
        },
    )
    return weekly_schedule


def process(user_id, alpaca_account_id, relationship_id, headers, payload):
    if initial_amount := payload.get("initialAmount"):
        transfer(
            user_id,
            alpaca_account_id,
            relationship_id,
            int(initial_amount),
            headers,
        )

    if weekly_topup := payload.get("weeklyTopup"):
        weekly_transfer(
            user_id,
            int(weekly_topup),
            headers,
        )


def valid_payload(payload) -> bool:
    if not (amount_str := payload.get("initialAmount")) or not (
        frequency_str := payload.get("weeklyTopup")
    ):
        return False

    try:
        amount = int(amount_str)
        assert amount > 0
    except Exception:
        log_error(
            "valid_payload",
            f"expect amounts to be always positive in {payload}",
        )
        return False
    try:
        weekly = int(frequency_str)
        assert weekly > 0
    except Exception:
        log_error(
            "valid_payload",
            f"expect weekly amounts to be always positive in {payload}",
        )
        return False

    return True


def trigger_rebalance(user_id: str, headers) -> bool:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    # Construct the task.
    task_id = str(uuid.uuid4())
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"https://api.nine30.com/v1/missions/rebalance/{user_id}",
            headers=headers,
        ),
        name=(
            client.task_path(
                project_id, location, rebalance_queue, task_id  # type: ignore
            )
            if task_id is not None
            else None
        ),
    )
    return bool(set_task(client, task))


def transfer_validator(request):
    """Implement GET /transfers/{transferId} end-point"""

    if not (transfer_id := request.args.get("transferId")):
        log_error("transfer_validator()", "failed to get transferId")
        abort(400)

    if not (user_id := request.args.get("userId")):
        log_error("transfer_validator()", "failed to get  userId")
        abort(403)

    if not (alpaca_account_id := get_alpaca_account_id(user_id=user_id)):
        log_error(
            "transfer_validator()",
            f"{user_id} does not have alpaca_account_id in database",
        )
        abort(400)

    transfers = get_transfers(alpaca_account_id)

    for transfer in transfers:
        if transfer["id"] == transfer_id:
            t = Transfer(user_id=user_id, details=transfer)

            # TODO: This may be too naive
            if t.status == "COMPLETE" and trigger_rebalance(
                user_id, request.headers
            ):
                print("Transfer completed, missions rebalance triggered")
                return ("OK", 200)
            elif t.status in {"REJECTED", "CANCELED", "RETURNED"}:
                return (f"transfer failed with {t.status}", 202)

            schedule_transfer_validator(user_id, transfer_id, request.headers)
            return ("rescheduled", 201)

    log_error(
        "transfer_validator()", f"cloud not find {transfer_id} in {transfers}"
    )
    return ("failed", 202)


def retry_till_linked(user_id, request):
    """Passive waiting till bank link is done"""
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PUT,
            url=f"https://api.nine30.com/v1/users/topup/{user_id}",
            body=json.dumps(request.get_json()).encode(),
            headers=request.headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )

    status = set_task(
        client,
        task,
        5 * 60,
    )

    print(f"set_task() completed with {status}")


def handle_users_topup(request):
    """Implement PUT /users/topup/{userId} end-point"""

    # validate API
    if not (user_id := request.args.get("userId")):
        log_error("handle_users_topup()", "missing user_id")
        abort(400)

    payload = request.get_json() if request.is_json else None

    if not payload or not valid_payload(payload):
        log_error("handle_users_topup()", f"invalid payload {payload}")
        abort(400)

    print(f"topup for {user_id}")

    if not (alpaca_account_id := get_alpaca_account_id(user_id=user_id)):
        log_error(
            "handle_users_topup()", f"user {user_id} does nor have an account"
        )
        abort(400)

    if not (
        relationship_id := get_from_user_vault(
            user_id=user_id, key="relationship_id"
        )
    ):
        log_error(
            "handle_users_topup()",
            f"user {user_id} is not linked with an bank account",
        )
        abort(400)

    link_status = bank_link_ready(alpaca_account_id, relationship_id)

    if link_status is None:
        return ("Failed, please check previous errors", 202)
    elif link_status == False:
        print(f"Bank Account Link not ready for {user_id}. Retry")
        retry_till_linked(user_id, request)
        return ("OK", 201)

    print("its all good! ready to progress")

    process(
        user_id=user_id,
        alpaca_account_id=alpaca_account_id,
        relationship_id=relationship_id,
        headers=request.headers,
        payload=payload,
    )

    return ("OK", 200)


@functions_framework.http
def topup(request):
    if request.method == "PUT":
        return handle_users_topup(request)
    if request.method == "GET":
        return transfer_validator(request)

    abort(405)
