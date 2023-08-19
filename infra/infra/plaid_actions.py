from infra.data.bank_account import Account
from infra.data.past_transactions import get_cursor, save_past_transactions
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy
from infra.proxies.plaid import plaid_proxy


def create_alpaca_link(
    plaid_access_token: str, account_id: str, alpaca_account_id: str
) -> str | None:
    """Create plaid <-> alpaca link"""

    r = plaid_proxy(
        method="POST",
        url="/processor/token/create",
        payload={
            "access_token": plaid_access_token,
            "processor": "alpaca",
            "account_id": account_id,
        },
        headers={"Content-Type": "application/json"},
        args=None,
    )

    if r.status_code != 200:
        log_error(
            "set_alpaca_link",
            "failed to create processor token w {r.status_code}.{r.text}",
        )
        return None

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{alpaca_account_id}/ach_relationships",
        payload={"processor_token": r.json()["processor_token"]},
        args=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "set_alpaca_link",
            "failed to create ach_relationship w {r.status_code}.{r.text}",
        )
        return None

    return r.json()["id"]


def get_access_token(public_token: str) -> tuple[str, str] | None:
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

    if not (item_id := plaid_payload.get("item_id")):
        log_error("get_access_token()", "failed to get item_id")
        return None
    return plaid_access_token, item_id


def load_recent_transactions(user_id: str, plaid_access_token: str) -> bool:
    cursor = get_cursor(user_id)
    has_more: bool = True
    while has_more:
        r = plaid_proxy(
            method="POST",
            url="/transactions/sync",
            payload={
                "access_token": plaid_access_token,
                "cursor": cursor,
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
            return False

        payload = r.json()

        cursor = payload["next_cursor"]
        has_more = payload["has_more"]

        if (
            len(payload["added"])
            or len(payload["modified"])
            or len(payload["removed"])
        ):
            save_past_transactions(
                user_id=user_id, cursor=cursor, data=payload  # type: ignore
            )

    return True


def load_new_accounts(user_id: str, plaid_access_token: str) -> bool:
    r = plaid_proxy(
        method="POST",
        url="/accounts/get",
        payload={
            "access_token": plaid_access_token,
        },
        headers={"Content-Type": "application/json"},
        args=None,
    )

    if r.status_code != 200:
        log_error(
            "get_recent_transactions()",
            "failed to called Plaid with {r.status_code}:{r.text}",
        )
        return False

    payload = r.json()

    for account in payload["accounts"]:
        Account.save(user_id=user_id, account_details=account)

    return True
