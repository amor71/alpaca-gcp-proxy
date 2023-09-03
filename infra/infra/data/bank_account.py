from google.cloud import firestore  # type: ignore


class Account:
    @classmethod
    def save(cls, user_id: str, account_details: dict) -> None:
        print(f"Account.save(): {user_id}:{account_details}")

        update_data = {"last_update": firestore.SERVER_TIMESTAMP}
        db = firestore.Client()
        doc_ref = db.collection("bank_accounts").document(user_id)

        _ = doc_ref.set(document_data=update_data, merge=True)

        _ = (
            doc_ref.collection("list")
            .document(account_details["account_id"])
            .set(document_data=account_details, merge=True)
        )

    @classmethod
    def get_account_ids(cls, user_id: str) -> list[str]:
        db = firestore.Client()

        accounts = (
            db.collection("bank_accounts")
            .document(user_id)
            .collection("list")
            .stream()
        )

        return [account.id for account in accounts]
