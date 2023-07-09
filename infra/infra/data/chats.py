import time

from google.cloud import firestore  # type: ignore


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
