from infra.data.past_transactions import get_cursor
from infra.logger import log_error
from infra.proxies.plaid import plaid_proxy


def get_access_token(public_token: str) -> str | None:
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


def get_recent_transactions(
    user_id: str, plaid_access_token: str
) -> dict | None:
    r = plaid_proxy(
        method="POST",
        url="/transactions/sync",
        payload={
            "access_token": plaid_access_token,
            "cursor": get_cursor(user_id),
            "count": 500,
            "options": {"include_personal_finance_category": True},
        },
        headers={"Content-Type": "application/json"},
        args=None,
    )

    if r.status_code != 200:
        log_error(
            "get_recent_transactions()",
            "failed to called Plaid with {r.status_code}:{r.text}",
        )
        return None

    return r.json()
