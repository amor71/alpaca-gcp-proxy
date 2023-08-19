from google.cloud import firestore  # type: ignore


class Account:
    @classmethod
    def save(cls, user_id: str, account_details: dict) -> None:
        print(f"Account.save(): {user_id}:{account_details}")

        update_data = {"last_update": firestore.SERVER_TIMESTAMP}
        db = firestore.Client()
        doc_ref = db.collection("bank_accounts").document(user_id)

        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set(update_data)
        else:
            doc_ref.update(update_data)

        account_doc_ref = doc_ref.collection("list").document(
            account_details["account_id"]
        )

        if not account_doc_ref.get().exists:
            account_doc_ref.set(account_details)
        else:
            account_doc_ref.update(account_details)

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
