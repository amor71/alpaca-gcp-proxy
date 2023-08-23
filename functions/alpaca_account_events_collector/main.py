import base64
import json

import functions_framework
from cloudevents.http.event import CloudEvent


@functions_framework.cloud_event
def alpaca_account_events_collector(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )

    print(f"alpaca_account_events_collector(): {message}")
