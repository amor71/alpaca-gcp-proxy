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
