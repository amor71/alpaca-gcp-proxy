from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore


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

    return float(payload["cash"])
