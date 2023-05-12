import os

# TODO: make env external
project_id = os.getenv("PROJECT_ID", None)
debug: bool = bool(os.getenv("DEBUG", "True"))
topic_id = os.getenv("TOPIC_ID", "new_user")
alpaca_events_topic_id = os.getenv("ALPACA_EVENTS_TOPIC_ID", "alpaca_events")
