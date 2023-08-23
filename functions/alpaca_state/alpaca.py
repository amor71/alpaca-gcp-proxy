import json

from google.cloud import firestore  # type: ignore

from infra.alpaca_action import process_account_update
from infra.data.alpaca_account import AlpacaAccount
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

    if r.status_code == 200:
        print("events_listener(): stream started")
        if r.encoding is None:
            r.encoding = "utf-8"

        for line in r.iter_lines(decode_unicode=True):
            if line and line[:6] == "data: ":
                payload = json.loads(line[6:])
                print(f"events_listener() received update {payload}")
                process_account_update(payload)


def alpaca_state_handler(user_id: str, payload: dict):
    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    update_data = {
        "alpaca_updated": firestore.SERVER_TIMESTAMP,
    }

    if alpaca_account_id := payload.get("id"):
        update_user_vault(user_id, "alpaca_account_id", alpaca_account_id)
    if relationship_id := payload.get("relationship_id"):
        update_user_vault(user_id, "relationship_id", relationship_id)
    if account_number := payload.get("account_number"):
        AlpacaAccount.save(account_number, user_id)

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type

    if doc_ref.get().exists:
        status = doc_ref.update(update_data)
    else:
        status = doc_ref.set(update_data)
