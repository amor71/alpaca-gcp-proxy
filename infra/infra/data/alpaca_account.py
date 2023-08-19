from google.cloud import firestore  # type: ignore


class AlpacaAccount:
    @classmethod
    def save(cls, account_number: str, user_id: str) -> None:
        print(f"AlpacaAccount.save(): {user_id}:{account_number}")

        data = {"updated_at": firestore.SERVER_TIMESTAMP, "user_id": user_id}
        db = firestore.Client()

        alpaca_account = db.collection("alpaca_accounts").document(
            account_number
        )
        if not alpaca_account.get().exists:
            alpaca_account.set(data)
        else:
            alpaca_account.update(data)

    @classmethod
    def load(cls, account_number: str) -> str | None:
        db = firestore.Client()
        doc = db.collection("alpaca_accounts").document(account_number).get()
        return doc.to_dict().get("user_id") if doc.exists else None
