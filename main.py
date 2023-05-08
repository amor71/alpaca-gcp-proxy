from time import time
from urllib.parse import urlparse

import functions_framework
from google.api_core.exceptions import NotFound
from requests import HTTPError

from apigateway.new_user.new_user import new_user_handler
from auth import get_bearer_token, is_token_invalid
from config import debug, project_id
from link import link
from logger import log
from proxies.alpaca import alpaca_proxy
from proxies.plaid import plaid_proxy
from proxies.stytch import stytch_proxy

omitted_response_headers: list = [
    "content-encoding",
    "Content-Encoding",
    "Transfer-Encoding",
    "transfer-encoding",
    "access-control-allow-headers",
    "Access-Control-Allow-Headers",
    "Via",
    "via",
    "Vary",
    "vary",
]


def failed_security(headers: dict) -> bool:
    return (
        headers.get("X-Appengine-Country") in ["RU", "SG", "DE", "NL", "IN"]
        or headers.get("X-Appengine-User-Ip")
        in ["143.42.55.206", "67.205.182.23"]
        or headers.get("X-Contact") in ["reresearch@protonmail.com"]
        or headers.get("Host") in ["us-predictions.live.fin.ag"]
    )


def _keep_header(header: str) -> bool:
    headers_to_remove: list[str] = [
        "X-",
        "Forwarded",
        "Traceparent",
        "Via",
        "Function-Execution-Id",
        "User-Agent",
        "Host",
        "Transfer-Encoding",
    ]

    return all(x not in header for x in headers_to_remove)


def clean_headers(headers: dict) -> dict:
    return {k: headers[k] for k in headers if _keep_header(k)}


# TODO: restrict CORS!
@functions_framework.http
def proxy(request):
    assert project_id, "PROJECT_ID not specified"

    # if failed_security(request.headers):
    #    print("security violation", request.url)
    #    return ("fuck you", 500)

    print(f"url {request.url}")

    token: str = get_bearer_token(request)
    headers: dict = clean_headers(dict(request.headers))
    if not token or is_token_invalid(token, headers):
        return ("invalid token passed", 403)

    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None

    if directories[0] in ["alpaca", "plaid", "stytch", "bank"]:
        add_response_headers = {"Access-Control-Allow-Headers": "*"}
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
                add_response_headers["Access-Control-Allow-Origin"] = "*"
            elif directories[0] == "plaid":
                if request.method == "OPTIONS":
                    headers = {
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Max-Age": "3600",
                    }

                    return ("", 204, headers)

                r = plaid_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    payload,
                    headers,
                )
                add_response_headers["Access-Control-Allow-Origin"] = "*"

            elif directories[0] == "stytch":
                r = stytch_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    args,
                    payload,
                    headers,
                )
            elif directories[1] == "link":
                if request.method == "OPTIONS":
                    # Allows GET requests from any origin with the Content-Type
                    # header and caches preflight response for an 3600s
                    headers = {
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Max-Age": "3600",
                    }

                    return ("", 204, headers)

                try:
                    r = link(request, headers)
                except HTTPError as e:
                    return (str(e), 400)

            response_headers = dict(r.headers)
            for header in omitted_response_headers:
                response_headers.pop(header, None)

            for k, v in add_response_headers.items():
                response_headers[k] = v

            if debug:
                t1 = time()
                log(
                    request=request,
                    response=r,
                    request_headers=headers,
                    response_headers=response_headers,
                    latency=t1 - t,
                )

            return (
                r.content,
                r.status_code,
                response_headers,
            )
        except NotFound:
            return ("secrets missing", 500)

    return ("proxy not found", 400)
