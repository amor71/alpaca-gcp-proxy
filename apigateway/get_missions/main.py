import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.plaid_actions import load_identities
from infra.stytch_actions import get_from_user_vault


@functions_framework.http
@auth
def get_missions(request):
    """implement GET /v1/missions"""

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "get_missions()",
            "could not load authenticated user_id, this shouldn't have happened",
        )
        return ("Something went wrong", 403)

    return ("OK", 200)
