import os

from requests import Request

from logger import log_error
from proxies.stytch import stytch_proxy

token_bypass = os.getenv("TOKEN_BYPASS", "moti")


def get_bearer_token(request: Request) -> str | None:
    """Extract 'Bearer' token from Authorization header"""
    if auth_header := request.headers.get("Authorization"):
        try:
            auth_header = auth_header.split()

            if auth_header[0] == "Bearer":
                return auth_header[1]
        except Exception as e:
            log_error("get_bearer_token()", str(e))

    return None


def authenticate_token(token: str, headers: dict) -> bool:
    """Authenticate session token w/ Stytch, return True is valid, otherwise False"""
    print("start authenticate_token", token)
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
