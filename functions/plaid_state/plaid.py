import time

from google.cloud import firestore  # type: ignore


def plaid_state_handler(user_id: str, payload: dict):
    print(f"email={user_id}, payload={payload}")

    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    update_data = {
        "plaid_updated": time.time_ns(),
    }

    if processor_token := payload.get("processor_token"):
        update_data["plaid_linked"] = True

    status = doc_ref.update(update_data)

    print("document update status=", status)
