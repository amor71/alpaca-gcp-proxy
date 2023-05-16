import json


def log_error(originator: str, error_message: str) -> None:
    """Log error to GCP logger"""
    entry = dict(
        severity="ERROR",
        message=f"{originator}: {error_message}",
    )
    print(json.dumps(entry))
