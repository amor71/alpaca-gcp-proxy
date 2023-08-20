import datetime
import json
import uuid
from enum import Enum

import functions_framework
from flask import abort
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from infra import auth, authenticated_user_id  # type: ignore
from infra.alpaca_action import (bank_link_ready, get_transfers,
                                 transfer_amount, validate_before_transfer)
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Missions
from infra.data.transfers import Transfer
from infra.logger import log_error
from infra.stytch_actions import get_alpaca_account_id, get_from_user_vault


class Frequency(Enum):
    immediate = 1
    weekly = 2
    monthly = 3


def set_task(
    client: tasks_v2.CloudTasksClient,
    task: tasks_v2.Task,
    second_from_now: int = 0,
) -> bool:
    if second_from_now:
        # Convert "seconds from now" to an absolute Protobuf Timestamp
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
    return True


def schedule_transfer_validator(id, headers):
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.GET,
            url=f"https://api.nine30.com/v1/transfers/{id}",
            headers=headers,
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    return set_task(client, task, 60 * 60 * 24)


def transfer(
    alpaca_account_id: str, relationship_id: str, amount: int, headers
) -> bool:
    """Initiate a transfer of 'amount' to user's alpaca account"""

    if not validate_before_transfer(alpaca_account_id):
        log_error(
            "transfer()",
            "{alpaca_account_id} account validation failed, aborting transfer",
        )
        return False

    if not (
        transfer_details := transfer_amount(
            alpaca_account_id, relationship_id, amount
        )
    ):
        return False

    transfer = Transfer(details=transfer_details)

    return schedule_transfer_validator(transfer.id, headers)


def schedule_transfer(amount: int, frequency: str, headers) -> bool:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())
    payload = [
        {"frequency": "immediate", "amount": amount},
        {"frequency": frequency, "amount": amount},
    ]

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PUT,
            url="https://api.nine30.com/v1/users/topup",
            headers=headers,
            body=json.dumps(payload).encode(),
        ),
        name=(
            client.task_path(project_id, location, rebalance_queue, task_id)  # type: ignore
            if task_id is not None
            else None
        ),
    )
    return set_task(
        client, task, 60 * 60 * 7 if frequency == "weekly" else 60 * 60 * 30
    )


def process(alpaca_account_id, relationship_id, headers, payload) -> bool:
    rc = False
    for item in payload:
        if payload["frequency"] == "immediate":
            rc |= transfer(
                alpaca_account_id,
                relationship_id,
                int(item["amount"]),
                headers,
            )
        else:
            rc |= schedule_transfer(
                int(item["amount"]),
                item["frequency"],
                headers,
            )

    return rc


def valid_payload(payload) -> bool:
    try:
        for item in payload:
            if not (amount_str := item.get("initialAmount")) or not (
                frequency_str := item.get("weeklyTopup")
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

    except Exception:
        return False

    return True


def trigger_rebalance(user_id: str, headers) -> bool:
    # Create a client.
    client = tasks_v2.CloudTasksClient()

    missions = Missions(user_id)

    for mission in missions:
        task_id = str(uuid.uuid4())
        payload = {
            "name": mission["name"],
            "strategy": mission["strategy"],
        }

        # Construct the task.
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url="https://api.nine30.com/v1/missions",
                headers=headers,
                body=json.dumps(payload).encode(),
            ),
            name=(
                client.task_path(
                    project_id, location, rebalance_queue, task_id  # type: ignore
                )
                if task_id is not None
                else None
            ),
        )
        if not set_task(client, task):
            return False

    return True


def transfer_validator(request):
    """Implement GET /transfers/{transferId} end-point"""

    if not (transfer_id := request.args.get("transferId")):
        abort(400)

    if not (user_id := authenticated_user_id.get()):
        log_error("handle_post", "could not load authenticated user_id")
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
            t = Transfer(details=transfer)

            # TODO: This may be too naive
            if t.status == "COMPLETE" and not trigger_rebalance(
                user_id, request.headers
            ):
                schedule_transfer_validator(transfer_id, request.headers)

            return ("OK", 200)

    log_error(
        "transfer_validator()", f"cloud not find {transfer_id} in {transfers}"
    )
    abort(400)


def handle_users_topup(request):
    """Implement PUT /users/topup end-point"""

    # validate API
    if not (user_id := request.args.get("userId")):
        abort(400)

    payload = request.get_json() if request.is_json else None

    if not payload or not valid_payload(payload):
        abort(400)

    print(f"topup for {user_id}")

    if not (alpaca_account_id := get_alpaca_account_id(user_id=user_id)):
        return ("brokerage account not provisioned yet", 400)
    if not (
        relationship_id := get_from_user_vault(
            user_id=user_id, key="relationship_id"
        )
    ):
        return ("brokerage account not linked to bank account yet", 400)

    if not bank_link_ready(user_id, relationship_id):
        print(f"Bank Account Link not ready for {user_id}. Retry")
        retry_topup(user_id, request)

    return ("OK", 200)

    if not process(
        alpaca_account_id=alpaca_account_id,
        relationship_id=relationship_id,
        headers=request.headers,
        payload=payload,
    ):
        return (
            "Failed to process request",
            400,
        )

    return ("OK", 200)


@functions_framework.http
def topup(request):
    if request.method == "PUT":
        return handle_users_topup(request)
    if request.method == "GET":
        return transfer_validator(request)

    abort(405)
