import time

from google.cloud import exceptions, firestore  # type: ignore

from ..logger import log_error


def save_chat(user_id: str, question: str, answer: str, id: str | None) -> str:
    db = firestore.Client()

    timestamp: int = time.time_ns()
    base_ref = db.collection("chats").document(user_id)
    session_id = id or str(timestamp)
    session_ref = base_ref.collection(session_id)

    meta_data = {"updated": timestamp, "summary": answer[:100]}
    status = session_ref.document("meta_data").set(meta_data)
    print("save_chat() : document update status=", status)

    status = session_ref.document().set(
        {"created": timestamp, "question": question, "answer": answer}
    )
    print("save_chat() : document update set=", status)

    return session_id


def get_chats_sessions(user_id: str) -> list[dict] | None:
    """Given a user_id -> return a list of all sessions.
    For each session include it's last update time, and summary.
    The list is ordered by created date (not last update)"""

    sessions = []
    db = firestore.Client()

    doc_ref = db.collection("chats").document(user_id)

    try:
        collections = doc_ref.collections()
    except exceptions.NotFound:
        log_error("get_chats_sessions", f"document {user_id} not found")
        return None

    for collection in collections:
        try:
            meta_data = collection.document("meta_data").get().to_dict()
        except exceptions.NotFound:
            log_error(
                "get_chats_sessions",
                f"session {collection.id} @ {user_id} does not have meta_data",
            )
            return None
        else:
            sessions.append(
                {
                    "sessionId": collection.id,
                    "updated": meta_data["updated"],
                    "summary": meta_data["summary"],
                }
            )

    return sessions


def get_chat_session_details(user_id: str, sessionId: str) -> list | None:
    chat_content = []
    db = firestore.Client()

    try:
        docs = (
            db.collection("chats")
            .document(user_id)
            .collection(sessionId)
            .stream()
        )
    except exceptions.NotFound:
        log_error(
            "get_chat_session_details",
            f"document {user_id}->collection({sessionId}) not found",
        )
        return None

    for document in docs:
        content = document.to_dict()
        print(f"content={content}")

        payload = {
            "question": content["question"],
            "answer": content["answer"],
        }
        if "created" in content:
            payload["created"] = content["created"]
        if "updated" in content:
            payload["updated"] = content["updated"]
        chat_content.append(payload)

    return chat_content
