import time

from google.cloud import firestore  # type: ignore

from infra.logger import log_error
from infra.proxies.stytch import stytch_proxy


def alpaca_state_handler(user_id: str, payload: dict):
    print(f"user-id={user_id}, payload={payload}")

    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    r = stytch_proxy(
        method="PUT",
        url=f"/v1/users/{user_id}",
        args=None,
        payload={"trusted_metadata": {"alpaca_account_id": payload.get("id")}},
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "alpaca_state_handler()",
            f"Updating Stytch failed {r.status_code}:{r.text}",
        )

    update_data = {
        "alpaca_updated": time.time_ns(),
    }

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if account_number := payload.get("account_number"):
        update_data["alpaca_account_number"] = account_number
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type
    if account_id := payload.get("account_id"):
        update_data["linked_bank_account_id"] = account_id
    if relationship_id := payload.get("relationship_id"):
        update_data["transfer_relationship_id"] = relationship_id
    status = doc_ref.update(update_data)
