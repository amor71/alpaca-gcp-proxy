import base64
import json

import functions_framework
from cloudevents.http.event import CloudEvent


@functions_framework.cloud_event
def post_ach_link(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    print(f"post_ach_link with message={message}")
