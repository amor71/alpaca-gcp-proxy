from google.cloud import firestore  # type: ignore

from ..logger import log_error


class Preferences:
    @classmethod
    def add(cls, user_id: str, data: dict) -> None:
        db = firestore.Client()
        doc = db.collection("preferences").document(user_id).get()

        if doc.exists:
            doc.update(data)
        else:
            doc.set(data)
