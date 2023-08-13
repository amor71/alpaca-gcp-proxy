from infra.logger import log_error
from infra.proxies.stytch import stytch_proxy  # type: ignore


def update_user_vault(user_id: str, key: str, value: str) -> bool:
    """Update key:value inside Stytch 'vault'"""
    r = stytch_proxy(
        method="PUT",
        url=f"/v1/users/{user_id}",
        args=None,
        payload={"trusted_metadata": {key: value}},
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "alpaca_state_handler()",
            f"Updating Stytch failed {r.status_code}:{r.text}",
        )
        return False

    return True


def get_from_user_vault(user_id: str, key: str) -> str | None:
    r = stytch_proxy(
        method="GET",
        url=f"v1/users/{user_id}",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "get_from_user_vault()",
            f"failed to load user {user_id}: {r.text}",
        )
        return None

    payload = r.json()

    return payload["trusted_metadata"].get(key)


def get_alpaca_account_id(user_id: str) -> str | None:
    """get alpaca_account_id from Stytch vault"""

    r = stytch_proxy(
        method="GET",
        url=f"v1/users/{user_id}",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "get_alpaca_account_id()",
            f"failed to load user {user_id}: {r.text}",
        )
        return None

    payload = r.json()

    return payload["trusted_metadata"].get("alpaca_account_id")
