from infra.logger import log_error
from infra.proxies.plaid import plaid_proxy  # type: ignore


def get_access_token(user_id: str, public_token: str) -> str | None:
    """convert public_key to a permanent access_token"""

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
        headers={"Content-Type": "application/json"},
        args=None,
    )
    if r.status_code != 200:
        log_error(
            "get_access_token()",
            f"failed call to Plaid with {r.status_code}:{r.text}",
        )
        return None

    plaid_payload = r.json()

    if not (plaid_access_token := plaid_payload.get("access_token")):
        log_error("get_access_token()", "failed to get access_token")
        return None

    return plaid_access_token
