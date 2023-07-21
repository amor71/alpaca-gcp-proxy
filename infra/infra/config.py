import os

project_id = os.getenv("PROJECT_ID", None)
location = os.getenv("LOCATION", None)
rebalance_queue = os.getenv("REBLANCE_QUEUE", None)
debug: bool = bool(os.getenv("DEBUG", "True"))
topic_id = os.getenv("TOPIC_ID", "new_user")
alpaca_events_topic_id = os.getenv("ALPACA_EVENTS_TOPIC_ID", "alpaca_events")
plaid_events_topic_id = os.getenv("PLAID_EVENTS_TOPIC_ID", "plaid_events")
