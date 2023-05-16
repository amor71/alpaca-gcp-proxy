import os

from flask import Request

from .logger import log_error
from .proxies.stytch import stytch_proxy

# TODO: remove bypass from code-base
token_bypass = os.getenv("TOKEN_BYPASS", "moti")
authorization_header = os.getenv("AUTH_HEADER", "X-Authorization")


def get_bearer_token(request: Request) -> str | None:
    """Extract 'Bearer' token from Authorization header"""
    if auth_header := request.headers.get(authorization_header):
        try:
            auth_headers = auth_header.split()

            print("auth headers", auth_headers)
            if auth_headers[0] == "Bearer":
                return auth_headers[1]
        except Exception as e:
            log_error("get_bearer_token()", str(e))

    return None


# TODO: remove prints
def authenticate_token(token: str, headers: dict) -> bool:
    """Authenticate session token w/ Stytch, return True is valid, otherwise False"""
    print("start authenticate_token", token, token_bypass)
    payload = {"session_token": token}

    # TODO: make a secret
    if token == token_bypass:
        return True

    r = stytch_proxy(
        method="POST",
        url="v1/sessions/authenticate",
        args=None,
        payload=payload,
        headers=headers,
    )
    print(r)
    print("end authenticate_token")

    return r.status_code == 200
