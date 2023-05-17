from flask import Request

from .auth import authenticate_token, get_bearer_token

cors_response_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
}


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


def auth(func):
    def handler(request: Request) -> tuple:
        print(f"url {request.url}")

        if request.method == "OPTIONS":
            return _handle_options()

        token = get_bearer_token(request)
        headers: dict = clean_headers(dict(request.headers))
        if not token or not authenticate_token(token, headers):
            return ("invalid token passed", 403)

        response: tuple = func(request)
        return _handle_cors_headers(response)

    return handler
