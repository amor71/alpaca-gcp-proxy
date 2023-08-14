import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.plaid_actions import get_access_token
from infra.stytch_actions import update_user_vault


def plaid_link(request):
    if not (public_token := request.args.get("publicToken")):
        log_error("plaid_link()", "can not get argument")
        abort(400)

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("plaid_link()", "could not load authenticated user_id")
        abort(400)

    if not (
        plaid_access_token := get_access_token(
            user_id=user_id, public_token=public_token
        )
    ):
        abort(400)

    if update_user_vault(
        user_id=user_id, key="plaid_access_token", value=plaid_access_token
    ):
        return ("OK", 200)

    abort(400)


@functions_framework.http
@auth
def plaid(request):
    """Implement  /v1/missions/plaid"""

    if request.method == "POST":
        return plaid_link(request)

    abort(405)
