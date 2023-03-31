from google.cloud import firestore


def new_user_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    doc_ref = db.collection("users").document("amichay")
    doc_ref.set({"first": "Ada", "last": "Lovelace", "born": 1815})
