from time import time
from urllib.parse import urlparse

import functions_framework
from google.api_core.exceptions import NotFound

from alpaca import alpaca_proxy
from config import debug, project_id
from logger import log
from plaid import plaid_proxy


@functions_framework.http
def link(request):
    ...


@functions_framework.http
def proxy(request):
    assert project_id, "PROJECT_ID not specified"
    parts = urlparse(request.url)
    args = list(request.args.items())
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None
    if directories[0] in ["alpaca", "plaid"]:
        try:
            t = time()

            r = (
                alpaca_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    args,
                    payload,
                )
                if directories[0] == "alpaca"
                else plaid_proxy(
                    request.method,
                    "/".join(directories[1:]),
                    payload,
                )
            )
            if debug:
                t1 = time()
                log(request=request, response=r, latency=t1 - t)
        except NotFound:
            return ("secrets missing", 500)

        return (r.content, r.status_code)

    return "proxy not found", 400
