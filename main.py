import json
import os
from time import time
from typing import Dict
from urllib.parse import urlparse

import functions_framework
import google_crc32c
from google.api_core.exceptions import NotFound
from google.cloud import secretmanager
from requests import Request, Response, request
from requests.auth import HTTPBasicAuth

api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"
plaid_client_id = "plaid_client_id"
plaid_secret = "plaid_secret"

project_id = os.getenv("PROJECT_ID", None)
debug: bool = bool(os.getenv("DEBUG", "True"))
alpaca_base_url = os.getenv(
    "ALPACA_BASE_URL", "https://broker-api.sandbox.alpaca.markets"
)
plaid_base_url = os.getenv("PLAID_BASE_URL", "https://sandbox.plaid.com")


def _construct_url(base_url: str, url: str) -> str:
    return (
        f"{base_url}/{url}"
        if base_url[-1] != "/"
        else f"{base_url[:-2]}/{url}"
    )


def _check_crc(arg0):
    # Verify payload checksum.
    crc32 = google_crc32c.Checksum()
    crc32.update(arg0.payload.data)
    assert arg0.payload.data_crc32c == int(
        crc32.hexdigest(), 16
    ), "data corruption"


def _get_alpaca_authentication() -> HTTPBasicAuth:
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


def _get_plaid_authentication() -> Dict:
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    api_key_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{plaid_client_id}/versions/latest"
        }
    )
    api_secret_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{plaid_secret}/versions/latest"
        }
    )

    _check_crc(api_key_response)
    _check_crc(api_secret_response)
    return {
        "client_id": api_key_response.payload.data.decode("UTF-8"),
        "secret": api_secret_response.payload.data.decode("UTF-8"),
    }


def alpaca_proxy(method: str, url: str, payload: str | None) -> Response:
    request_url = _construct_url(alpaca_base_url, url)
    auth = _get_alpaca_authentication()
    return (
        request(method=method, url=request_url, json=payload, auth=auth)
        if payload
        else request(method=method, url=request_url, auth=auth)
    )


def plaid_proxy(method: str, url: str, payload: Dict | None) -> Response:
    request_url = _construct_url(plaid_base_url, url)
    auth = _get_plaid_authentication()

    if payload:
        payload.update(auth)

    return request(
        method=method,
        url=request_url,
        json=payload,
    )


def log(request: Request, response: Response, latency: float) -> None:
    # Build structured log messages as an object
    global_log_fields = {
        "request_headers": dict(request.headers),
        "response_headers": dict(response.headers),
        "request_url": request.url,
        "status_code": response.status_code,
        "reason": response.reason,
        "response_url": response.url,
        "method": request.method,
        "request_payload": request.json,
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
    assert project_id, "PROJECT_ID not specified"
    parts = urlparse(request.url)
    directories = parts.path.strip("/").split("/")
    payload = request.get_json() if request.is_json else None
    if directories[0] in ["alpaca", "plaid"]:
        try:
            t = time()

            r = (
                alpaca_proxy(
                    request.method,
                    "/".join(directories[1:]),
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
