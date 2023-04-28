import base64
import json
from time import time
from urllib.parse import urlparse

import functions_framework
from cloudevents.http.event import CloudEvent
from google.api_core.exceptions import NotFound

from alpaca import alpaca_proxy
from config import debug, project_id
from events.alpaca import alpaca_state_handler
from events.new_user import new_user_handler
from link import link
from logger import log
from plaid import plaid_proxy
from stytch import stytch_proxy


@functions_framework.cloud_event
def new_user(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    new_user_handler(message)


@functions_framework.cloud_event
def alpaca_state(cloud_event: CloudEvent):
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    alpaca_state_handler(message)


def failed_security(headers: dict) -> bool:
    return (
        headers.get("X-Appengine-Country") in ["RU", "SG", "DE", "NL", "IN"]
        or headers.get("X-Appengine-User-Ip")
        in ["143.42.55.206", "67.205.182.23"]
        or headers.get("X-Contact") in ["reresearch@protonmail.com"]
        or headers.get("Host") in ["us-predictions.live.fin.ag"]
    )


@functions_framework.http
def proxy(request):
    assert project_id, "PROJECT_ID not specified"

    if failed_security(request.headers):
        print("security violation", request.url)
        return ("fuck you", 500)

    print(f"url {request.url}")
    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None

    print("starting")

    if directories[0] in ["alpaca", "plaid", "stytch", "bank"]:
        # Set CORS headers for the preflight request
        if request.method == "OPTIONS":
            # Allows GET requests from any origin with the Content-Type
            # header and caches preflight response for an 3600s
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "3600",
            }

            return ("", 204, headers)

        try:
            t = time()
            if directories[0] == "alpaca":
                r = alpaca_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    args,
                    payload,
                )
            elif directories[0] == "plaid":
                r = plaid_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    payload,
                )
            elif directories[0] == "stytch":
                r = stytch_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    args,
                    payload,
                )
            elif directories[1] == "link":
                r = link(request)

            if debug:
                t1 = time()
                log(request=request, response=r, latency=t1 - t)
        except NotFound:
            return ("secrets missing", 500)

        # TODO:  restrict to nine30 sub-domain, handle headers
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
        return (r.content, r.status_code, headers)

    return ("proxy not found", 400)
