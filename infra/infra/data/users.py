from google.cloud import firestore  # type: ignore

from ..logger import log_error


class User:
    def __init__(self, user_id: str | None = None) -> None:
        self.user_id = user_id
        self.data = self._load_user() if user_id else None

    def __getattr__(self, name):
        return self.data.get(name) if self.exists() else None

    @property
    def exists(self) -> bool:
        """Return True if User object is populated with data"""

        return self.data != None

    def _load_user(self) -> dict | None:
        """Load document from Firestore, based on the user-id"""

        db = firestore.Client()
        doc_ref = db.collection("users").document(self.user_id)

        doc = doc_ref.get()
        if not doc.exists:
            log_error("USer", f"could not load {self.user_id} document")
            return None

        return doc.to_dict()

    @classmethod
    def update(cls, user_id: str, payload: dict) -> None:
        """Update user details with details in payload"""

        db = firestore.Client()
        db.collection("users").document(user_id).set(
            document_data=payload, merge=True
        )


class Identity:
    @classmethod
    def save(cls, user_id: str, account_details: dict) -> None:
        update_data = {"last_update": firestore.SERVER_TIMESTAMP}
        db = firestore.Client()
        doc_ref = (
            db.collection("identity")
            .document(user_id)
            .set(document_data=update_data, merge=True)
        )

        _ = (
            doc_ref.collection("list")
            .document(account_details["account_id"])
            .set(document_data=account_details, merge=True)
        )

    @classmethod
    def load(cls, user_id: str) -> list[dict] | None:
        update_data = {"last_update": firestore.SERVER_TIMESTAMP}
        db = firestore.Client()
        doc_ref = db.collection("identity").document(user_id)

        if not doc_ref.get().exists:
            return None

        docs = doc_ref.collection("list").stream()

        return [doc.to_dict() for doc in docs]
