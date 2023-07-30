from google.cloud import firestore  # type: ignore

from ..logger import log_error


class Preferences:
    @classmethod
    def add(cls, user_id: str, data: dict) -> None:
        db = firestore.Client()
        doc_ref = db.collection("preferences").document(user_id)
        if doc_ref.get().exists:
            doc_ref.update(data)
        else:
            doc_ref.set(data)
