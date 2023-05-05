import base64

from requests import Request

from logger import log, log_error
from proxies.stytch import stytch_proxy


def get_bearer_token(request: Request) -> str | None:
    if auth_header := request.headers.get("Authorization"):
        try:
            auth_header = auth_header.split()

            if auth_header[0] == "Bearer":
                return auth_header[1]
        except Exception as e:
            log_error("get_bearer_token()", str(e))

    return None


def is_token_invalid(token: str, headers: dict) -> bool:
    print("start is_token_invalid", token)
    encoded_token = base64.b64encode(bytes(token, "utf-8"))
    encoded_token_str = encoded_token.decode("utf-8")
    print("encoded", encoded_token_str)
    payload = {"session_token": encoded_token_str}
    r = stytch_proxy(
        method="POST",
        url="v1/sessions/authenticate",
        args=None,
        payload=payload,
        headers=headers,
    )
    print(r)
    print(r.json())
    print("end is_token_invalid")

    return False
