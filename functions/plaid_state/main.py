import base64
import json

import functions_framework
from cloudevents.http.event import CloudEvent

from .plaid import plaid_state_handler


@functions_framework.cloud_event
def plaid_state(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    print(f"plaid_state message={message}")

    plaid_state_handler(message["user_id"], message["payload"])
