from urllib.parse import urlparse

import functions_framework
from flask import Request
from link import link
from requests import HTTPError, Response

from infra import auth, clean_headers  # type: ignore
from infra.logger import log
from infra.proxies.alpaca import alpaca_proxy
from infra.proxies.plaid import plaid_proxy
from infra.proxies.stytch import stytch_proxy

proxy_mapper: dict = {
    "alpaca": alpaca_proxy,
    "plaid": plaid_proxy,
    "stytch": stytch_proxy,
}
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


def _build_response(response: Response) -> tuple:
    response_headers = dict(response.headers)
    for header in omitted_response_headers:
        response_headers.pop(header, None)

    return (
        response.content,
        response.status_code,
        response_headers,
    )


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

    if directories[0] in proxy_mapper:
        r = proxy_mapper[directories[0]](
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

    return _build_response(response=r)


@functions_framework.http
@auth
def proxy(request: Request) -> tuple:
    """proxy endpoint"""

    return _proxy_dispatcher(
        method=request.method,
        directories=urlparse(request.url).path.strip("/").split("/"),
        args=list(request.args.items()),
        payload=request.get_json() if request.is_json else None,
        headers=clean_headers(dict(request.headers)),
        request=request,
    )
