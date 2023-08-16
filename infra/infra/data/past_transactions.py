from google.cloud import firestore


def save_past_transactions(user_id: str, cursor: str, data: dict) -> None:
    print(f"save_past_transactions: {user_id}:{data}")

    db = firestore.Client()
    doc_ref = db.collection("plaid_transactions").document(user_id)
    doc_ref.update({"cursor": cursor})
    new_transactions = doc_ref.collection("transactions").document()
    new_transactions(data)


def get_cursor(user_id: str) -> str | None:
    db = firestore.Client()
    doc_ref = db.collection("plaid_transactions").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    data = doc.to_dict()
    return data.get("cursor")
