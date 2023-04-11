from datetime import datetime, timezone

from google.cloud import firestore  # type: ignore


def new_user_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    doc_ref = db.collection("users").document(payload["email_id"])
    status = doc_ref.set(
        {
            "user_id": payload["user_id"],
            "state": 0,
            "create_at": datetime.now(timezone.utc),
        }
    )
    print("document write status=", status)
