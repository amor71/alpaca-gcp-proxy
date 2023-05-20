from time import time
from urllib.parse import urlparse

import functions_framework
from flask import Request
from google.api_core.exceptions import NotFound
from link import link
from requests import HTTPError

from infra import auth, clean_headers  # type: ignore
from infra.config import debug
from infra.logger import log
from infra.proxies.alpaca import alpaca_proxy
from infra.proxies.plaid import plaid_proxy
from infra.proxies.stytch import stytch_proxy

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


def _supported_proxies(requested_proxy: str) -> bool:
    return requested_proxy in {"alpaca", "plaid", "stytch", "bank"}


def _proxy_dispatcher(
    method: str,
    directories: list,
    args: list,
    payload: dict | None,
    headers: dict,
    request: Request,
) -> tuple:
    if not _supported_proxies(directories[0]):
        return ("proxy not found", 400)

    add_response_headers = {"Access-Control-Allow-Headers": "*"}

    if directories[0] == "alpaca":
        r = alpaca_proxy(
            method,
            "/".join(directories[1:]),
            args,
            payload,
            headers,
        )
        add_response_headers["Access-Control-Allow-Origin"] = "*"
    elif directories[0] == "plaid":
        r = plaid_proxy(
            method,
            "/".join(directories[1:]),
            payload,
            headers,
        )
        add_response_headers["Access-Control-Allow-Origin"] = "*"

    elif directories[0] == "stytch":
        r = stytch_proxy(
            method,
            "/".join(directories[1:]),
            args,
            payload,
            headers,
        )
    elif directories[1] == "link":
        try:
            r = link(request, headers)
        except HTTPError as e:
            return (str(e), 400)

    response_headers = dict(r.headers)
    for header in omitted_response_headers:
        response_headers.pop(header, None)

    for k, v in add_response_headers.items():
        response_headers[k] = v

    return (
        r.content,
        r.status_code,
        response_headers,
    )


@functions_framework.http
@auth
def proxy(request: Request) -> tuple:
    """proxy endpoint"""

    t0 = time()

    headers: dict = clean_headers(dict(request.headers))
    r = _proxy_dispatcher(
        method=request.method,
        directories=urlparse(request.url).path.strip("/").split("/"),
        args=list(request.args.items()),
        payload=request.get_json() if request.is_json else None,
        headers=headers,
        request=request,
    )

    if debug:
        t1 = time()
        log(
            request=request,
            response=r,
            request_headers=headers,
            response_headers=r[2] if len(r) == 3 else {},
            latency=t1 - t0,
        )

    return r
