from google.cloud import firestore  # type: ignore


class AlpacaEvents:
    @classmethod
    def add(cls, event_entity: str, event_id: str) -> None:
        data = {"updated_at": firestore.SERVER_TIMESTAMP, "event_id": event_id}
        db = firestore.Client()
        db.collection(f"alpaca_events_{event_entity}").add(data)

    @classmethod
    def latest_event_id(cls, event_entity: str) -> list[dict] | None:
        db = firestore.Client()

        collection = db.collection(f"alpaca_events_{event_entity}")
        query = collection.order_by(
            "updated_at", direction=firestore.Query.DESCENDING
        ).limit(1)
        doc = query.get()[0]
        return doc.to_dict()
