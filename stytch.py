import os

from google.cloud import secretmanager
from requests import Response, request
from requests.auth import HTTPBasicAuth

from config import project_id
from proxy_base import check_crc, construct_url

stytch_project = "stytch_project_id"
stytch_secret = "stytch_secret"


base_url = os.getenv("STYTCH_BASE_URL", "https://test.stytch.com/v1/")


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

    print(api_key_response.payload.data.decode("UTF-8"))
    print(api_secret_response.payload.data.decode("UTF-8"))
    return HTTPBasicAuth(
        username=api_key_response.payload.data.decode("UTF-8"),
        password=api_secret_response.payload.data.decode("UTF-8"),
    )


def trigger_step_function(url: str, response: dict):
    if "login_or_create" in url:
        # and response["user_created"] == True:
        print(f"new user created with payload {response}")


def stytch_proxy(
    method: str, url: str, args: list, payload: str | None
) -> Response:
    request_url = construct_url(base_url, url)
    print(request_url)
    auth = _get_authentication()
    r = (
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

    trigger_step_function(url, r.json())
    return r
