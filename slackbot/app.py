import logging
import os
from typing import Callable

import requests
# Use the package we installed
from slack_bolt import App, BoltContext, Say

logging.basicConfig(level=logging.DEBUG)

# Initializes your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)


@app.middleware
def log_request(logger: logging.Logger, body: dict, next: Callable):
    logger.debug(body)
    return next()


# https://api.slack.com/events/message
# Newly posted messages only
# or @app.event("message")
@app.event({"type": "message", "subtype": None})
def reply_in_thread(body: dict, say: Say):
    event = body["event"]

    base_url: str = "https://api.nine30.com"
    headers = {"X-Authorization": "Bearer moti"}

    url = f"{base_url}/v1/chatbot"

    payload = {"question": event["text"]}
    r = requests.post(url=url, headers=headers, json=payload)

    thread_ts = event.get("thread_ts", None) or event["ts"]
    say(text=r.json()["answer"], thread_ts=thread_ts)


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 8080)))
