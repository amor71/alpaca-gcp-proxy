import json
import os
from concurrent import futures
from typing import Dict

from google.cloud import pubsub_v1, secretmanager  # type:ignore
from requests import Response, request

from .. import authenticated_user_id
from ..config import plaid_events_topic_id, project_id
from ..logger import log_error
from ..proxies.proxy_base import check_crc, construct_url

plaid_base_url = os.getenv("PLAID_BASE_URL", "https://sandbox.plaid.com")

plaid_client_id = "plaid_client_id"
plaid_secret_name = "plaid_secret"  # nosec

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
            "name": f"projects/{project_id}/secrets/{plaid_secret_name}/versions/latest"
        }
    )

    check_crc(api_key_response)
    check_crc(api_secret_response)
    return {
        "client_id": api_key_response.payload.data.decode("UTF-8"),
        "secret": api_secret_response.payload.data.decode("UTF-8"),
    }


def trigger_step_function(user_id: str, url: str, response: dict):
    print(f"trigger_step_function {user_id}, {url}, {response}")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, plaid_events_topic_id)
    publish_future = publisher.publish(
        topic_path,
        json.dumps({"user_id": user_id, "payload": response}).encode("utf-8"),
    )

    futures.wait([publish_future])
    print("triggered step_function")


def plaid_proxy(
    method: str,
    url: str,
    args: list | None,
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
