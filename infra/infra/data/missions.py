import time

from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


class Missions:
    def __init__(self, user_id: str | None = None) -> None:
        self.data = self._load_missions() if user_id else None

    @property
    def exists(self) -> bool:
        """Return True if User object is populated with data"""

        return self.data != None

    def __iter__(self):
        if not self.exists:
            return None

        yield from self.data

    def _load_missions(self):
        db = firestore.Client()

        doc_ref = db.collection("missions").document(self.user_id)
        if not doc_ref.exists:
            log_error(
                "Missions",
                f"could not load missions for user_id {self.user_id}",
            )
            return None

        docs = doc_ref.collection("user_missions").stream()

        return [doc_ref.to_dict() for doc_ref in docs]

    @classmethod
    def add(cls, user_id: str, mission_name: str, strategy: str) -> str:
        data = {
            "name": mission_name,
            "strategy": strategy,
            "created": time.time_ns(),
        }

        db = firestore.Client()
        doc_ref = (
            db.collection("missions")
            .document(user_id)
            .collection("user_missions")
            .document()
        )

        _ = doc_ref.set(data)

        return doc_ref.id


class Runs:
    def __init__(self, data: dict):
        self.data = data

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def strategy(self) -> str:
        return self.data["strategy"]

    @classmethod
    def add(
        cls, run_id: str, user_id: str, mission_name: str, strategy: str
    ) -> str:
        data = {
            "name": mission_name,
            "strategy": strategy,
            "created": time.time_ns(),
        }

        db = firestore.Client()

        run_doc_def = db.collection("runs").document(run_id)
        _ = run_doc_def.set(data)

        return run_doc_def.id

    @classmethod
    def load(cls, run_id: str) -> "Runs" | None:
        db = firestore.Client()
        doc = db.collection("runs").document(run_id).get()

        if doc.exists:
            return Runs(doc.to_dict())

        log_error("reschedule_run_by_run_id", "could not load run {run_id}")
        return None
