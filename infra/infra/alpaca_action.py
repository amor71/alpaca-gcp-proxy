from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore


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

    return float(payload["cash"]) > 0.0


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
