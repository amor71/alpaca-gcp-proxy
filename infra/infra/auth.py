import os

from flask import Request, abort

from .logger import log_error
from .proxies.stytch import stytch_proxy

token_bypass = os.getenv("TOKEN_BYPASS")
authorization_header = os.getenv("AUTH_HEADER", "X-Authorization")


def get_bearer_token(request: Request) -> str | None:
    """Extract 'Bearer' token from Authorization header"""
    if auth_header := request.headers.get(authorization_header):
        try:
            auth_headers = auth_header.split()
            if auth_headers[0] == "Bearer":
                return auth_headers[1]
        except Exception as e:
            log_error("get_bearer_token()", str(e))
    else:
        log_error("get_bearer_token", f"{authorization_header} not present")

    return None


def authenticate_token(token: str, headers: dict) -> str | None:
    """Authenticate session token w/ Stytch, return user_id is valid, otherwise raise 403"""

    payload = {"session_token": token}

    if token == token_bypass:
        return "bypass"

    r = stytch_proxy(
        method="POST",
        url="v1/sessions/authenticate",
        args=None,
        payload=payload,
        headers=headers,
    )

    if r.status_code == 200:
        return r.json().get("session").get("user_id")

    print(r.status_code, r.text)
    abort(403)
