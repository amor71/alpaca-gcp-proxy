from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


def save_past_transactions(user_id: str, data: dict) -> None:
    print(f"save_past_transactions: {user_id}:{data}")


def get_cursor(user_id: str) -> str | None:
    db = firestore.Client()
    doc_ref = db.collection("plaid_transactions").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    data = doc.to_dict()
    return data.get("cursor")
