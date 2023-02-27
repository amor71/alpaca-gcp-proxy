import os
import functions_framework
from urllib.parse import urlparse

from requests.auth import HTTPBasicAuth
from requests import request, Response
from google.cloud import secretmanager
import google_crc32c
from google.api_core.exceptions import NotFound


api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"

project_id = os.getenv("PROJECT_ID", None)
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

    print(f"{method} Alpaca Proxy for {request_url}")
    if payload:
        print(f"payload {payload}")

    auth = get_alpaca_authentication()
    return (
        request(method=method, url=request_url, json=payload, auth=auth)
        if payload
        else request(method=method, url=url, auth=auth)
    )


@functions_framework.http
def proxy(request):
    print(request)
    print(request.method)
    parts = urlparse(request.url)
    directories = parts.path.strip("/").split("/")

    if directories[0] == "proxy" and directories[1] == "alpaca":
        payload = request.get_json() if request.is_json else None

        try:
            r = alpaca_proxy(request.method, "/".join(directories[2:]), payload)
        except NotFound as e:
            return "secrets missing", 500

        return (r.json, 200) if r.status_code == 200 else (r.reason, r.status_code)

    return "proxy not found", 400
