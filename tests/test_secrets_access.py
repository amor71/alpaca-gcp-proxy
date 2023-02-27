import os
from google.cloud import secretmanager
import google_crc32c
from google.api_core.exceptions import NotFound

api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"

project_id = os.getenv("PROJECT_ID", None)


def test_secret_alpaca_api_key() -> None:
    assert project_id, "missing GCP project_id"
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    name = client.secret_path(project_id, api_key_name)

    # Get the secret.
    response = client.get_secret(request={"name": name})

    print(response)


def test_access_alpaca_api_key() -> None:
    assert project_id, "missing GCP project_id"
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    name = client.secret_path(project_id, api_key_name)

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{api_key_name}/versions/latest"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Verify payload checksum.
    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    assert response.payload.data_crc32c == int(
        crc32c.hexdigest(), 16
    ), "data corruption"

    payload = response.payload.data.decode("UTF-8")
    assert payload, "missing secret value"


def test_access_alpaca_api_key_negative() -> None:
    assert project_id, "missing GCP project_id"
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret.
    name = client.secret_path(project_id, api_key_name)

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/does_not_exist/versions/latest"

    # Access the secret version.
    try:
        response = client.access_secret_version(request={"name": name})
    except NotFound:
        return
    else:
        raise AssertionError("expect failure")
