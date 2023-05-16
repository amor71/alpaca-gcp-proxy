from flask import Request

from .auth import authenticate_token, get_bearer_token


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


def auth(func):
    def handler(request: Request):
        print(f"url {request.url}")
        print(f"headers {request.headers}")
        if request.method == "OPTIONS":
            return_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "3600",
            }

            return ("", 204, return_headers)

        token = get_bearer_token(request)
        headers: dict = clean_headers(dict(request.headers))
        if not token or not authenticate_token(token, headers):
            return ("invalid token passed", 403)

        return func(request)

    return handler
