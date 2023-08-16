from google.cloud import firestore


def save_past_transactions(user_id: str, cursor: str, data: dict) -> None:
    print(f"save_past_transactions: {user_id}:{data}")

    cursor_payload = {"cursor": cursor}
    db = firestore.Client()
    doc_ref = db.collection("plaid_transactions").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        doc_ref.set(cursor_payload)
    else:
        doc_ref.update(cursor_payload)

    transactions = doc_ref.collection("transactions")

    for new_transaction in data["added"]:
        transactions.document(new_transaction["transaction_id"]).set(
            new_transaction
        )
    for modified_transaction in data["modified"]:
        transactions.document(modified_transaction["transaction_id"]).update(
            modified_transaction
        )
    for removed_transaction in data["removed"]:
        transactions.document(removed_transaction["transaction_id"]).delete()


def get_cursor(user_id: str) -> str | None:
    db = firestore.Client()
    doc_ref = db.collection("plaid_transactions").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    data = doc.to_dict()
    return data.get("cursor")
