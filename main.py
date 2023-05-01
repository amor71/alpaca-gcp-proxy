from time import time
from urllib.parse import urlparse

import functions_framework
from google.api_core.exceptions import NotFound
from requests.exceptions import JSONDecodeError

from alpaca import alpaca_proxy
from apigateway.new_user.new_user import new_user_handler
from auth import get_bearer_token, is_token_invalid
from config import debug, project_id
from link import link
from logger import log
from plaid import plaid_proxy
from stytch import stytch_proxy


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
    token = get_bearer_token(request)
    if token and is_token_invalid(token):
        return ("invalid token passed", 403)

    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None
    headers = request.headers

    if directories[0] in ["alpaca", "plaid", "stytch", "bank"]:
        # Set CORS headers for the preflight request
        # if request.method == "OPTIONS":
        #    # Allows GET requests from any origin with the Content-Type
        #    # header and caches preflight response for an 3600s
        #    headers = {
        #        "Access-Control-Allow-Origin": "*",
        #        "Access-Control-Allow-Methods": "*",
        #        "Access-Control-Allow-Headers": "*",
        #        "Access-Control-Max-Age": "3600",
        #    }
        #
        #    return ("", 204, headers)

        try:
            t = time()
            if directories[0] == "alpaca":
                r = alpaca_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    args,
                    payload,
                    headers,
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

        try:
            print("encoding", r.encoding)
            encoding = r.headers.get("content-encoding")

            if encoding == "gzip":
                payload = r.text
            else:
                payload = r.json()

        except JSONDecodeError:
            payload = r.content
        return (
            payload,
            r.status_code,
            r.headers.items(),
        )

    return ("proxy not found", 400)
