import time

from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


class Account:
    @classmethod
    def save(cls, user_id: str, account_details: dict) -> None:
        print(f"Account.save(): {user_id}:{account_details}")

        update_data = {"last_update": time.time_ns()}
        db = firestore.Client()
        doc_ref = db.collection("back_accounts").document(user_id)

        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set(update_data)
        else:
            doc_ref.update(update_data)

        accounts_collection = doc_ref.collection("list")
        account = accounts_collection.document(account_details["account_id"])
        account.set(account_details)
