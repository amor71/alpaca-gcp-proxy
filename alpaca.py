import os

from google.cloud import secretmanager
from requests import Response, request
from requests.auth import HTTPBasicAuth

from config import project_id
from proxy_base import check_crc, construct_url

api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"


alpaca_base_url = os.getenv(
    "ALPACA_BASE_URL", "https://broker-api.sandbox.alpaca.markets"
)


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

    check_crc(api_key_response)
    check_crc(api_secret_response)
    return HTTPBasicAuth(
        username=api_key_response.payload.data.decode("UTF-8"),
        password=api_secret_response.payload.data.decode("UTF-8"),
    )


def alpaca_proxy(
    method: str, url: str, args: list, payload: str | None
) -> Response:
    request_url = construct_url(alpaca_base_url, url)
    auth = _get_alpaca_authentication()
    return (
        request(
            method=method,
            params=args,
            url=request_url,
            json=payload,
            auth=auth,
        )
        if payload
        else request(method=method, params=args, url=request_url, auth=auth)
    )
