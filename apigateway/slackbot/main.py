import json

import functions_framework
import slack
from google.cloud import secretmanager  # type:ignore

from infra import auth  # type:ignore
from infra.config import project_id  # type:ignore
from infra.proxies.proxy_base import check_crc  # type:ignore

slack_signing_secret = "openai_api_key"


def _get_credentials() -> str:
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    slack_signing_secret_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{slack_signing_secret}/versions/latest"
        }
    )

    check_crc(slack_signing_secret_response)

    return slack_signing_secret_response.payload.data.decode("UTF-8")


# Function to send a message to Slack
def send_slack_message(channel, message):
    # Set up the Slack API client
    client = slack.WebClient(token=_get_credentials())

    # Send the message
    client.chat_postMessage(channel=channel, text=message)


@functions_framework.http
def slackbot(request):
    """Implement GET/POST /v1/slackbot"""

    print(request.headers)

    if not request.data:
        print(f"args={request.args}")
        return ("OK", 200)

    event_data = json.loads(request.data.decode("utf-8"))

    # Check if the event is a message event
    if (
        event_data["type"] == "event_callback"
        and "message" in event_data["event"]
    ):
        message = event_data["event"]["message"]
        user = message.get("user")
        text = message.get("text")
        channel = message["channel"]

        # Add your custom logic here to process and respond to the received message

        # Example: Reply to the message
        if user and text:
            reply = f"Thanks for your message, <@{user}>! You said: {text}"
            send_slack_message(channel, reply)

    # Respond with a 200 status code to acknowledge the event
    return ("", 200)
