import time

import telemetrics
from google.cloud import firestore  # type: ignore


def new_user_handler(user_id: str):
    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)
    status = doc_ref.set(
        {
            "created": time.time_ns(),
        }
    )

    telemetrics.increment_new_user()
    print("document write status=", status)
