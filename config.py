import os

project_id = os.getenv("PROJECT_ID", None)
debug: bool = bool(os.getenv("DEBUG", "True"))
topic_id = os.getenv("TOPIC_ID", None)
