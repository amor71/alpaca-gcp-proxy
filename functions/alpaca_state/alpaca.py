import json
import time

from google.cloud import firestore  # type: ignore

from infra.proxies.alpaca import alpaca_proxy
from infra.stytch_actions import update_user_vault


def events_listener():
    r = alpaca_proxy(
        method="GET",
        url="/v1/events/accounts/status",
        args=None,
        payload=None,
        headers={"accept": "text/event-stream"},
        stream=True,
    )

    print(f"status : {r.status_code}")

    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                print("line", json.loads(line))


def alpaca_state_handler(user_id: str, payload: dict):
    print(f"user-id={user_id}, payload={payload}")

    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    update_data = {
        "alpaca_updated": time.time_ns(),
    }

    if alpaca_account_id := payload.get("id"):
        update_user_vault(user_id, "alpaca_account_id", alpaca_account_id)
    if relationship_id := payload.get("relationship_id"):
        update_user_vault(user_id, "relationship_id", relationship_id)

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if account_number := payload.get("account_number"):
        update_data["alpaca_account_number"] = account_number
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type
    # if account_id := payload.get("account_id"):
    #    update_data["linked_bank_account_id"] = account_id

    if doc_ref.get().exists:
        status = doc_ref.update(update_data)
    else:
        status = doc_ref.set(update_data)
