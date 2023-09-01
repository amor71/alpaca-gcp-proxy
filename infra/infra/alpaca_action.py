import json
from concurrent import futures

from google.cloud import pubsub_v1  # type:ignore

from infra.config import post_ach_link_topic_id, project_id
from infra.data.alpaca_account import AlpacaAccount
from infra.data.alpaca_events import AlpacaEvents
from infra.data.bank_account import Account
from infra.data.users import User
from infra.logger import log_error
from infra.plaid_actions import create_alpaca_link
from infra.proxies.alpaca import alpaca_proxy  # type: ignore
from infra.stytch_actions import get_from_user_vault, update_user_vault


def bank_link_ready(account_id: str, relationship_id: str) -> bool | None:
    r = alpaca_proxy(
        method="GET",
        url=f"/v1/accounts/{account_id}/ach_relationships",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "bank_link_ready()",
            f"failed to load account {account_id}: {r.text}",
        )
        return None

    payload = r.json()
    print(f"payload = {payload}")

    for link in payload:
        if link.get("id") == relationship_id:
            print("found:", link)
            if link.get("status") == "APPROVED":
                return True
            elif link.get("status") in {"QUEUED", "SENT_TO_CLEARING"}:
                return False

            return None

    return None


def get_available_cash(account_id: str) -> float | None:
    """Get amount of available cash for trading"""

    r = alpaca_proxy(
        method="GET",
        url=f"/v1/trading/accounts/{account_id}/account",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "get_available_cash()",
            f"failed to load account {account_id}: {r.text}",
        )
        return None

    payload = r.json()

    if payload["account_blocked"] == True:
        log_error("get_available_cash()", f"{account_id} blocked")
        return None

    print(f"account_id: {account_id}, details:{payload}")
    return float(payload["cash"])


def get_model_portfolio_by_name(name: str) -> dict | None:
    """Look-up a portfolio by portfolio name"""

    r = alpaca_proxy(
        method="GET",
        url="/v1/beta/rebalancing/portfolios",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        return None

    portfolios = r.json()
    return next(
        (
            portfolio
            for portfolio in portfolios
            if portfolio["name"].lower() == name.lower()
            and portfolio["status"] == "active"
        ),
        None,
    )


def validate_before_transfer(account_id: str) -> bool:
    """Validate account has cash and it's not blocked"""

    r = alpaca_proxy(
        method="GET",
        url=f"/v1/trading/accounts/{account_id}/account",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "get_available_cash()",
            f"failed to load account {account_id}: {r.text}",
        )
        return False

    payload = r.json()

    if payload["account_blocked"] == True:
        log_error("get_available_cash()", f"{account_id} blocked")
        return False

    return True


def get_account_balance(alpaca_account_id: str) -> int | None:
    r = alpaca_proxy(
        method="GET",
        url=f"v1/accounts/{alpaca_account_id}",
        args=None,
        headers=None,
        payload=None,
    )

    if r.status_code != 200:
        log_error(
            "get_account_balance()",
            f"failed to get account details {alpaca_account_id}: {r.text}",
        )
        return None

    payload = r.json()
    print(payload)
    usd = payload.get("usd")

    portfolio_value = int(usd.get("portfolio_value", 0))
    cash = int(usd.get("cash", 0))

    print(
        f"account balances for {alpaca_account_id}: {portfolio_value}, {cash}"
    )

    return portfolio_value + cash


def transfer_amount(
    alpaca_account_id: str, relationship_id: str, amount: int
) -> dict | None:
    """Trigger funding"""

    payload = {
        "transfer_type": "ach",
        "relationship_id": relationship_id,
        "amount": str(amount),
        "direction": "INCOMING",
    }

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{alpaca_account_id}/transfers",
        args=None,
        payload=payload,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "transfer_amount()",
            f"failed to initiate transfer for {alpaca_account_id}: {r.text}",
        )
        return None

    return r.json()


def get_transfers(alpaca_account_id: str):
    """Get all transfer entities in account"""

    r = alpaca_proxy(
        method="GET",
        url=f"/v1/accounts/{alpaca_account_id}/transfers",
        args=None,
        headers=None,
        payload=None,
    )

    if r.status_code != 200:
        log_error(
            "get_transfers()",
            f"failed to get account transfers with {r.text}",
        )
        return None

    return r.json()


def handle_alpaca_activated(user_id, alpaca_account_id):
    # Get Plaid access token
    if not (
        plaid_access_token := get_from_user_vault(
            user_id, "plaid_access_token"
        )
    ):
        log_error(
            "handle_alpaca_activated()",
            f"failed to get plaid_access_token for {user_id}",
        )
        return

    # Get user account-id from DB
    account_ids = Account.get_account_ids(user_id)

    if not account_ids:
        log_error(
            "handle_alpaca_activated()",
            f"failed to load account-id for user {user_id}",
        )
        return

    # Create plaid alpaca link
    ach_relationship_id = create_alpaca_link(
        plaid_access_token, account_ids[0], alpaca_account_id
    )

    # Store relationship-id
    update_user_vault(user_id, "relationship_id", ach_relationship_id)

    trigger_post_ach_link(user_id)


def trigger_post_ach_link(user_id: str):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, post_ach_link_topic_id)
    publish_future = publisher.publish(
        topic_path,
        json.dumps({"user_id": user_id}).encode("utf-8"),
    )

    futures.wait([publish_future])
    print("triggered post_ach_link function")


def process_account_update(payload: dict) -> None:
    """Process account update event"""

    # get user-id from account_number
    account_number = payload["account_number"]
    user_id = AlpacaAccount.load(account_number)

    if not user_id:
        log_error("process_account_update()", "can't load user_id")
        return

    if not (alpaca_account_id := payload.get("account_id")):
        log_error(
            "process_account_update()",
            f"payload {payload} does not have account_id",
        )
        return

    # TODO: consider handling crypto account approvals too
    if payload.get("status_to") == "ACTIVE":
        User.update(user_id, {"onboardingCompleted": True})
        handle_alpaca_activated(user_id, alpaca_account_id)

    # Update user record
    User.update(user_id, payload)
    User.update(user_id, {"alpaca": True})

    # Store event-id = mark event as processed
    AlpacaEvents.add("accounts", payload["event_id"])
