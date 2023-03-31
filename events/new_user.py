from datetime import datetime, timezone

from google.cloud import firestore


def new_user_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    print("db", db)

    doc_ref = db.collection("users").document(payload["email_id"])

    print("doc_ref", doc_ref)
    status = doc_ref.set(
        {
            "user_id": payload["user_ud"],
            "state": 0,
            "create_at": datetime.now(timezone.utc),
        }
    )

    print("status=", status)
