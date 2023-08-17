from google.cloud import firestore  # type: ignore


class PlaidItem:
    @classmethod
    def save(cls, item_id: str, user_id: str) -> None:
        print(f"PlaidItem.save(): {user_id}:{item_id}")

        data = {"created": firestore.SERVER_TIMESTAMP, "user_id": user_id}
        db = firestore.Client()
        _ = db.collection("plaid_items").document(item_id).set(data)

    @classmethod
    def load(cls, item_id: str) -> str | None:
        db = firestore.Client()
        doc = db.collection("plaid_items").document(item_id).get()
        return doc.to_dict().get("user_id") if doc.exists else None
