from google.cloud import firestore  # type: ignore

from ..logger import log_error


class Transfer:
    def __init__(
        self, user_id: str, details: dict | None = None, id: str | None = None
    ) -> None:
        self.data = None
        if details:
            self.data = details
            self.user_id = user_id
            self.id = details["id"]
            self._save()
        elif id:
            self.id = id

            self._load()

    @property
    def exists(self) -> bool:
        """Return True if User object is populated with data"""

        return self.data != None

    @property
    def status(self) -> str | None:
        """Return transfer status"""

        return self.data.get("status") if self.data else None

    def _save(self) -> None:
        """Save transfer details as a document in Firestore"""

        if not self.data:
            return
        db = firestore.Client()
        doc_ref = db.collection("transfers").document(self.user_id)
        doc_ref.set(
            document_data={"updated": firestore.SERVER_TIMESTAMP}, merge=True
        )
        doc_ref.collection("list").document(self.data["id"]).set(
            document_data=self.data, merge=True
        )

    def _load(self) -> None:
        """Load transfer details document from Firestore"""

        db = firestore.Client()
        doc_ref = (
            db.collection("transfers")
            .document(self.user_id)
            .collection("list")
            .document(self.id)
        )

        if not doc_ref.exists:
            log_error("Transfer", "cant load transfer with id {self.id}")
            return

        self.data = doc_ref.get().to_dict()
