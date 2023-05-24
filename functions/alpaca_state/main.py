import base64
import json

import functions_framework
from cloudevents.http.event import CloudEvent

from .alpaca import alpaca_state_handler


@functions_framework.cloud_event
def alpaca_state(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    print(f"alpaca_state message={message}")

    alpaca_state_handler(message["email_id"], message["payload"])
