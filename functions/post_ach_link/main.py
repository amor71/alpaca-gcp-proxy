import base64
import datetime
import json
import uuid

import functions_framework
from cloudevents.http.event import CloudEvent
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Missions
from infra.logger import log_error


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


def handle_mission(user_id: str, mission: dict) -> None:
    client = tasks_v2.CloudTasksClient()

    task_id = str(uuid.uuid4())

    payload = {
        "initialAmount": mission.get("initial_amount"),
        "weeklyTopup": mission.get("weekly_topup"),
    }

    print(f"calling topup w/ {payload}")
    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.PUT,
            url=f"https://api.nine30.com/v1/users/topup/{user_id}",
            body=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
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
    )

    print(f"set_task() completed with {status}")


@functions_framework.cloud_event
def post_ach_link(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    print(f"post_ach_link with message={message}")

    if not (user_id := message.get("user_id")):
        log_error("post_ach_link()", "missing user_id in payload")
        return

    missions = Missions(user_id)

    for mission in missions:
        handle_mission(user_id, mission)
