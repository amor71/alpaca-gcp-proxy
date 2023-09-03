import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.plaid_actions import load_new_accounts
from infra.stytch_actions import get_from_user_vault


def load_accounts(request):
    """Implement GET /v1/plaid/accounts"""

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "load_accounts()",
            "could not load authenticated user_id",
        )
        abort(400)

    if not (
        plaid_access_token := get_from_user_vault(
            user_id=user_id, key="plaid_access_token"
        )
    ):
        log_error(
            "load_accounts()",
            "'plaid_access_token' can't be loaded from user's vault ",
        )
        abort(400)

    if not load_new_accounts(user_id, plaid_access_token):
        abort(400)

    return ("OK", 200)


@functions_framework.http
@auth
def plaid_accounts(request):
    if request.method == "GET":
        return load_accounts(request)

    abort(405)
