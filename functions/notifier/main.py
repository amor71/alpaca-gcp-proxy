import json

import requests

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"


def slackNotifier(request):
    def send_slack_notification(message):
        headers = {"Content-type": "application/json"}
        payload = {"text": message}

        response = requests.post(
            SLACK_WEBHOOK_URL, headers=headers, data=json.dumps(payload)
        )

        if response.status_code == 200:
            print("Notification sent successfully")
        else:
            print("Failed to send notification")

    message = (
        "Slack Message Sent Directly from GCP following Terraform Deployment"
    )
    send_slack_notification(message=message)
    return message
