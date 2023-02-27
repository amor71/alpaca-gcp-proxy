
import functions_framework
from urllib.parse import urlparse

from requests.auth import HTTPBasicAuth
from google.cloud import secretmanager

api_key_name = "alpaca_api_key"
api_secret_name = "alpaca_api_secret"


def get_alpaca_authentication() -> HTTPBasicAuth:
    client = secretmanager.SecretManagerServiceClient()

    # Build the parent name from the project.
    # Create the parent secret.
    api_key = client.get_secret(name=api_key_name)

    print(api_key)


# Add the secret version.
version = client.add_secret_version(
    request={"parent": secret.name, "payload": {"data": b"hello world!"}}
)

# Access the secret version.
response = client.access_secret_version(request={"name": version.name})

# Print the secret payload.
#
# WARNING: Do not print the secret in a production environment - this
# snippet is showing how to access the secret material.
payload = response.payload.data.decode("UTF-8")
print("Plaintext: {}".format(payload))


def alpaca_proxy(method: str, url: str, payload: str | None) -> str:
    if payload:
        print(f"payload {payload}")

    auth = get_alpaca_authentication()
    print(auth)
    return f"{method} Alpaca Proxy for {url}"


@functions_framework.http
def proxy(request):
    print(request)
    print(request.method)
    parts = urlparse(request.url)
    directories = parts.path.strip("/").split("/")

    if directories[0] == "proxy" and directories[1] == "alpaca":
        payload = request.get_json() if request.is_json else None
        return alpaca_proxy(request.method, "/".join(directories[2:]), payload)

    return "proxy not found", 400
