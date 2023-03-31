from google.cloud import firestore


def new_user_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    print("db", db)

    doc_ref = db.collection("users").document("amichay")

    print("doc_ref", doc_ref)
    status = doc_ref.set({"first": "Ada", "last": "Lovelace", "born": 1815})

    print("status=", status)
