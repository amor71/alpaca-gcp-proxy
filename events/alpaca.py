from datetime import datetime, timezone

from google.cloud import firestore  # type: ignore

from telemetry import add_new_alpaca_application


def alpaca_state_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    doc_ref = db.collection("users").document(payload["email_id"])
    status = doc_ref.set(
        {
            "user_id": payload["user_id"],
            "state": 1,
            "modified_at": datetime.now(timezone.utc),
        }
    )

    add_new_alpaca_application()
    print("document write status=", status)
