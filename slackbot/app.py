import os

# Use the package we installed
from slack_bolt import App, BoltContext, Say

# Initializes your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)


# https://api.slack.com/events/message
# Newly posted messages only
# or @app.event("message")
@app.event({"type": "message", "subtype": None})
def reply_in_thread(body: dict, say: Say):
    print(f"body={body}")
    event = body["event"]
    thread_ts = event.get("thread_ts", None) or event["ts"]
    say(text="Hey, what's up?", thread_ts=thread_ts)


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 8080)))
