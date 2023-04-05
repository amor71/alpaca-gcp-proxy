import base64
import json
from time import time
from urllib.parse import urlparse

import functions_framework
from cloudevents.http.event import CloudEvent
from google.api_core.exceptions import NotFound

from alpaca import alpaca_proxy
from config import debug, project_id
from events.new_user import new_user_handler
from logger import log
from plaid import plaid_proxy
from stytch import stytch_proxy


@functions_framework.cloud_event
def new_user(cloud_event: CloudEvent):
    print("here", cloud_event, type(cloud_event))
    print("data", cloud_event.data)
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    new_user_handler(message)


def link(request):
    print(request)

    try:
        payload = request.get_json()
        public_token = payload["public_token"]
        account_id = payload["account_id"]
    except Exception:
        return ("JSON body must include 'public_token' and 'account_id", 400)

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
    )
    print(f"response {r} {r.json()}")

    if r.status_code == 400:
        return r

    r = plaid_proxy(
        method="POST",
        url="/processor/token/create",
        payload={
            "access_token": r.json()["access_token"],
            "processor": "alpaca",
        },
    )

    if r.status_code == 400:
        return r

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{account_id}/ach_relationships",
        payload={r.json()["processor_token"]},
    )

    return r


@functions_framework.http
def proxy(request):
    assert project_id, "PROJECT_ID not specified"

    print(request.headers, request)
    if request.headers["X-Appengine-Country"] == "RU":
        return ("fuck you", 500)

    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None

    print(payload)
    print(directories[0])
    if directories[0] in ["alpaca", "plaid", "stytch", "link"]:
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
            else:
                r = link(request)

            if debug:
                t1 = time()
                log(request=request, response=r, latency=t1 - t)
        except NotFound:
            return ("secrets missing", 500)

        return (r.content, r.status_code)

    return ("proxy not found", 400)
