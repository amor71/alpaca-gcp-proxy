import json

from requests import Request, Response
from requests.exceptions import JSONDecodeError

from config import project_id


def log_error(originator: str, error_message: str) -> None:
    entry = dict(
        severity="ERROR",
        message=f"{originator}: {error_message}",
    )
    print(json.dumps(entry))


def log(request: Request, response: Response, latency: float) -> None:
    # Build structured log messages as an object
    try:
        json_response = response.json()
    except JSONDecodeError:
        json_response = ""

    global_log_fields = {
        "request_headers": dict(request.headers),
        "response_headers": dict(response.headers),
        "request_url": request.url,
        "status_code": response.status_code,
        "reason": response.reason,
        "response_url": response.url,
        "method": request.method,
        "request_payload": request.json if request.is_json else None,  # type: ignore
        "response_payload": json_response,
        "latency": latency,
    }

    # Add log correlation to nest all log messages.
    # This is only relevant in HTTP-based contexts, and is ignored elsewhere.
    # (In particular, non-HTTP-based Cloud Functions.)
    request_is_defined = "request" in globals() or "request" in locals()
    if request_is_defined and request:
        if trace_header := request.headers.get("X-Cloud-Trace-Context"):
            trace = trace_header.split("/")
            global_log_fields[
                "logging.googleapis.com/trace"
            ] = f"projects/{project_id}/traces/{trace[0]}"

    # Complete a structured log entry.
    entry = dict(
        severity="DEBUG",
        message="request",
        # Log viewer accesses 'component' as jsonPayload.component'.
        component="arbitrary-property",
        **global_log_fields,
    )

    print(json.dumps(entry))
