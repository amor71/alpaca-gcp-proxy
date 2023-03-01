import os
import json
import functions_framework
from sys import getsizeof
from urllib.parse import urlparse

from requests.auth import HTTPBasicAuth
from requests import request, Response, Request
from google.cloud import secretmanager
import google_crc32c
from google.api_core.exceptions import NotFound
from typing import Dict
from time import time

api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"

project_id = os.getenv("PROJECT_ID", None)
debug: bool = bool(os.getenv("DEBUG", "True"))
alpaca_base_url = os.getenv(
    "ALPACA_BASE_URL", "https://broker-api.sandbox.alpaca.markets"
)


def get_alpaca_authentication() -> HTTPBasicAuth:
    assert project_id, "missing GCP project_id"
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    api_key_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{api_key_name}/versions/latest"
        }
    )
    api_secret_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{api_secret_name}/versions/latest"
        }
    )

    _check_crc(api_key_response)
    _check_crc(api_secret_response)
    return HTTPBasicAuth(
        username=api_key_response.payload.data.decode("UTF-8"),
        password=api_secret_response.payload.data.decode("UTF-8"),
    )


def _check_crc(arg0):
    # Verify payload checksum.
    crc32 = google_crc32c.Checksum()
    crc32.update(arg0.payload.data)
    assert arg0.payload.data_crc32c == int(crc32.hexdigest(), 16), "data corruption"


def alpaca_proxy(method: str, url: str, payload: str | None) -> Response:
    request_url = (
        f"{alpaca_base_url}/{url}"
        if alpaca_base_url[-1] != "/"
        else f"{alpaca_base_url[:-2]}/{url}"
    )

    auth = get_alpaca_authentication()
    return (
        request(method=method, url=request_url, json=payload, auth=auth)
        if payload
        else request(method=method, url=request_url, auth=auth)
    )


def log(request: Request, response: Response, latency: float) -> None:
    # Build structured log messages as an object.
    global_log_fields = {
        "request_headers": dict(request.headers),
        "response_headers": dict(response.headers),
        "request_url": request.url,
        "status_code": response.status_code,
        "reason": response.reason,
        "response_url": response.url,
        "method": request.method,
        "request_payload": request.json if request.is_json else None,
        "response_payload": response.json(),
        "latency": latency,
    }

    # Add log correlation to nest all log messages.
    # This is only relevant in HTTP-based contexts, and is ignored elsewhere.
    # (In particular, non-HTTP-based Cloud Functions.)
    request_is_defined = "request" in globals() or "request" in locals()
    if request_is_defined and request:
        if trace_header := request.headers.get("X-Cloud-Trace-Context"):
            trace = trace_header.split("/")
            global_log_fields[
                "logging.googleapis.com/trace"
            ] = f"projects/{project_id}/traces/{trace[0]}"

    # Complete a structured log entry.
    entry = dict(
        severity="DEBUG",
        message="request",
        # Log viewer accesses 'component' as jsonPayload.component'.
        component="arbitrary-property",
        **global_log_fields,
    )

    print(json.dumps(entry))


@functions_framework.http
def proxy(request):
    assert project_id, "project_id not specified"
    parts = urlparse(request.url)
    directories = parts.path.strip("/").split("/")

    if directories[0] == "proxy" and directories[1] == "alpaca":
        payload = request.get_json() if request.is_json else None

        try:
            t = time()
            r = alpaca_proxy(request.method, "/".join(directories[2:]), payload)
            if debug:
                t1 = time()
                log(request=request, response=r, latency=t1 - t)
        except NotFound as e:
            return ("secrets missing", 500)

        return (r.content, r.status_code)

    return "proxy not found", 400
