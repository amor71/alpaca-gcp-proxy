import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth  # type: ignore


def process(email_id) -> dict | None:
    db = firestore.Client()

    document_ref = db.collection("users").document(email_id)
    doc = document_ref.get()

    return doc.to_dict() if doc.exists else None


@functions_framework.http
@auth
def get_user_details(request):
    email_id = request.args.get("emailId")

    # TODO: Validate email belong to authenticated user

    payload = process(email_id=email_id)

    return (payload, 200) if payload else ("user does not exist", 404)
