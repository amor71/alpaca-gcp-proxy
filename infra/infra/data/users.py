from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


class User:
    def __init__(self, user_id: str | None = None) -> None:
        self.user_id = user_id
        self.data = self._load_user() if user_id else None

    @property
    def exists(self) -> bool:
        """Return True if User object is populated with data"""

        return self.data != None

    @property
    def alpaca_account_id(self) -> str | None:
        """Return the Alpaca account id, if exists in data. Otherwise None"""

        return self.data.get("alpaca_account_id") if self.data else None

    @property
    def transfer_relationship_id(self) -> str | None:
        """Return the Alpaca id to be used in transfer requests, if exists. Otherwise None"""

        return self.data.get("transfer_relationship_id") if self.data else None

    def _load_user(self) -> dict | None:
        """Load document from Firestore, based on the user-id"""

        db = firestore.Client()
        doc_ref = db.collection("users").document(self.user_id)

        doc = doc_ref.get()
        if not doc.exists:
            log_error(
                "load_account_id", f"could not load {self.user_id} document"
            )
            return None

        return doc.to_dict()
