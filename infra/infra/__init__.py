from contextvars import ContextVar

from flask import Request

from .auth import authenticate_token, get_bearer_token

cors_response_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
}

request_email_id: ContextVar = ContextVar("email_id")


def _keep_header(header: str) -> bool:
    headers_to_remove: list[str] = [
        "X-",
        "Forwarded",
        "Traceparent",
        "Via",
        "Function-Execution-Id",
        "User-Agent",
        "Host",
        "Transfer-Encoding",
    ]

    return all(x not in header for x in headers_to_remove)


def clean_headers(headers: dict) -> dict:
    """Sanitize request headers"""
    return {k: headers[k] for k in headers if _keep_header(k)}


def _handle_options() -> tuple:
    return_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "3600",
    }
    return ("", 204, return_headers)


def _handle_cors_headers(response: tuple) -> tuple:
    if len(response) == 2:
        return response + (cors_response_headers,)

    return_headers: dict = response[2]
    for k, v in cors_response_headers.items():
        if k not in return_headers:
            return_headers[k] = v

    return response[:2] + (return_headers,)


# TODO: restrict CORS!
def auth(func):
    """Decorator to authenticate request and add CORS support"""

    def handler(request: Request) -> tuple:
        print(f"url {request.url}")

        if request.method == "OPTIONS":
            return _handle_options()

        if not (token := get_bearer_token(request)):
            return ("invalid token passed", 403)

        email_id = request.args.get("emailId")

        request_email_id.set(email_id)
        print(f"set request_email_id {email_id}")
        headers: dict = clean_headers(dict(request.headers))
        authenticated_user = authenticate_token(token, headers)

        print(f"authenticated_user={authenticated_user} email_id={email_id}")
        if not authenticated_user or (
            email_id
            and authenticated_user
            not in [
                email_id,
                "bypass",
            ]
        ):
            return ("invalid token passed", 403)

        response: tuple = func(request)
        return _handle_cors_headers(response)

    return handler
