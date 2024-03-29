import os

from google.cloud import pubsub_v1, secretmanager  # type:ignore
from requests import HTTPError, Response, request
from requests.auth import HTTPBasicAuth

from ..config import project_id, topic_id
from ..proxies.proxy_base import check_crc, construct_url

stytch_project = "stytch_project_id"
stytch_secret = "stytch_secret"


base_url = os.getenv("STYTCH_BASE_URL", "https://test.stytch.com/")


def _get_authentication() -> HTTPBasicAuth:
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    api_key_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{stytch_project}/versions/latest"
        }
    )
    api_secret_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{stytch_secret}/versions/latest"
        }
    )

    check_crc(api_key_response)
    check_crc(api_secret_response)

    return HTTPBasicAuth(
        username=api_key_response.payload.data.decode("UTF-8"),
        password=api_secret_response.payload.data.decode("UTF-8"),
    )


def stytch_proxy(
    method: str,
    url: str,
    args: list | None,
    payload: dict | None,
    headers: dict | None,
) -> Response:
    request_url = construct_url(base_url, url)
    auth = _get_authentication()

    return (
        request(
            method=method,
            # params=args,
            url=request_url,
            json=payload,
            auth=auth,
            # headers=headers,
        )
        if payload
        else request(
            method=method,
            params=args,
            url=request_url,
            auth=auth,
            headers=headers,
        )
    )
