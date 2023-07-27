import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error


def process(user_id: str) -> dict | None:
    db = firestore.Client()

    document_ref = db.collection("users").document(user_id)
    doc = document_ref.get()

    return doc.to_dict() if doc.exists else None


@functions_framework.http
@auth
def get_user_details(request):
    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "new_user()",
            "could not load authenticated user_id, this shouldn't have happened",
        )
        return ("Something went wrong", 403)

    # TODO: Validate email belong to authenticated user

    payload = process(user_id)

    return (payload, 200) if payload else ("user does not exist", 404)
