import os
from typing import Dict

from google.cloud import secretmanager
from requests import Response, request

from proxy_base import check_crc, construct_url

plaid_base_url = os.getenv("PLAID_BASE_URL", "https://sandbox.plaid.com")

plaid_client_id = "plaid_client_id"
plaid_secret = "plaid_secret"

project_id = os.getenv("PROJECT_ID", None)


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

    check_crc(api_key_response)
    check_crc(api_secret_response)
    return {
        "client_id": api_key_response.payload.data.decode("UTF-8"),
        "secret": api_secret_response.payload.data.decode("UTF-8"),
    }


def plaid_proxy(
    method: str,
    url: str,
    payload: Dict | None,
    headers: dict | None,
) -> Response:
    print("plaid_proxy", url, method)
    request_url = construct_url(plaid_base_url, url)
    auth = _get_plaid_authentication()

    if payload:
        payload.update(auth)

    return request(
        method=method,
        url=request_url,
        json=payload,
        headers=headers,
    )
