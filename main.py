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
    message = json.loads(
        base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    )
    new_user_handler(message)


def link(request):
    print(request)

    args = list(request.args.items())

    try:
        payload = request.get_json()
        public_token = payload["public_token"]
        alpaca_account_id = payload["alpaca_account_id"]
        plaid_account_id = payload["plaid_account_id"]
    except Exception:
        return ("JSON body must include 'public_token' and 'account_id", 400)

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
    )
    print(f"response 1 {r} {r.json()}")
    if r.status_code != 200:
        return r

    r = plaid_proxy(
        method="POST",
        url="/processor/token/create",
        payload={
            "access_token": r.json()["access_token"],
            "processor": "alpaca",
            "account_id": plaid_account_id,
        },
    )

    print(f"response 2 {r} {r.json()}")
    if r.status_code == 400:
        return r

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{alpaca_account_id}/ach_relationships",
        payload={"processor_token": r.json()["processor_token"]},
        args=args,
    )

    print(f"response 3 {r} {r.json()}")
    return r


def failed_security(headers: dict) -> bool:
    return (
        headers.get("X-Appengine-Country", None)
        in ["RU", "SG", "DE", "NL", "IN"]
        or headers.get("X-Appengine-User-Ip", None)
        in ["143.42.55.206", "67.205.182.23"]
        or headers.get("X-Contact", None) in ["reresearch@protonmail.com"]
        or headers.get("Host", None) in ["us-predictions.live.fin.ag"]
    )


@functions_framework.http
def proxy(request):
    assert project_id, "PROJECT_ID not specified"

    if failed_security(request.headers):
        return ("fuck you", 500)

    print(request.headers, request)

    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None

    print(payload)
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
