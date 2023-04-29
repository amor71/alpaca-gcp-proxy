import json

from requests import Request

from logger import log_error
from stytch import stytch_proxy


def get_bearer_token(request: Request) -> str | None:
    if auth_header := request.headers.get("Authorization"):
        try:
            auth_header = auth_header.split()

            if auth_header[0] == "Bearer":
                return auth_header[1]
        except Exception as e:
            log_error("get_bearer_token()", str(e))

    return None


def is_token_invalid(token: str) -> bool:
    payload = {"session_token": token}
    r = stytch_proxy(
        method="GET",
        url="v1/sessions/authenticate",
        args=None,
        payload=json.dumps(payload),
    )
    print(r)
    print(r.json())

    return False
