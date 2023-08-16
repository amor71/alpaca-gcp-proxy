import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.past_transactions import save_past_transactions
from infra.logger import log_error
from infra.plaid_actions import get_access_token, get_recent_transactions
from infra.stytch_actions import get_from_user_vault, update_user_vault


def plaid_link(request):
    """Implement POST  /v1/missions/plaid"""

    if not (public_token := request.args.get("publicToken")):
        log_error("plaid_link()", "can not get argument")
        abort(400)

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("plaid_link()", "could not load authenticated user_id")
        abort(400)

    if not (plaid_access_token := get_access_token(public_token=public_token)):
        abort(400)

    if update_user_vault(
        user_id=user_id, key="plaid_access_token", value=plaid_access_token
    ):
        return ("OK", 200)

    abort(400)


def load_recent_transactions(request):
    """Implement GET /v1/plaid/transactions"""

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "load_recent_transactions()",
            "could not load authenticated user_id",
        )
        abort(400)

    if not (
        plaid_access_token := get_from_user_vault(
            user_id=user_id, key="plaid_access_token"
        )
    ):
        log_error(
            "load_recent_transactions()",
            "'plaid_access_token' can't be loaded from user's vault ",
        )
        abort(400)

    if not (payload := get_recent_transactions(user_id, plaid_access_token)):
        log_error(
            "load_recent_transactions()",
            "'plaid_access_token' can't be loaded from user's vault ",
        )
        abort(400)

    _ = save_past_transactions(user_id, payload)

    return ("OK", 200)


@functions_framework.http
@auth
def plaid(request):
    if request.method == "POST":
        return plaid_link(request)
    elif request.method == "GET":
        return load_recent_transactions(request)

    abort(405)
