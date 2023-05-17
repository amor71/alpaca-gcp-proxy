import os

from flask import Request

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

    return None


def authenticate_token(token: str, headers: dict) -> bool:
    """Authenticate session token w/ Stytch, return True is valid, otherwise False"""

    payload = {"session_token": token}

    if token == token_bypass:
        return True

    r = stytch_proxy(
        method="POST",
        url="v1/sessions/authenticate",
        args=None,
        payload=payload,
        headers=headers,
    )

    # TODO: remove after debug
    print(f"Stytch authenticate_token returned {r} w/ {r.text}")

    return r.status_code == 200
