import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.plaid_item import PlaidItem
from infra.data.users import User
from infra.logger import log_error
from infra.plaid_actions import (get_access_token, load_new_accounts,
                                 load_recent_transactions)
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

    plaid_access_token, item_id = get_access_token(public_token=public_token)
    if not plaid_access_token:
        abort(400)

    if not update_user_vault(
        user_id=user_id, key="plaid_access_token", value=plaid_access_token
    ):
        abort(400)

    User.update(user_id=user_id, payload={"plaid": True})
    PlaidItem.save(item_id=item_id, user_id=user_id)

    # load transactions
    load_recent_transactions(user_id, plaid_access_token)

    # load accounts
    load_new_accounts(user_id, plaid_access_token)

    return ("OK", 200)


def load_transactions(request):
    """Implement GET /v1/plaid/transactions"""

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "load_transactions()",
            "could not load authenticated user_id",
        )
        abort(400)

    if not (
        plaid_access_token := get_from_user_vault(
            user_id=user_id, key="plaid_access_token"
        )
    ):
        log_error(
            "load_transactions()",
            "'plaid_access_token' can't be loaded from user's vault ",
        )
        abort(400)

    if not load_recent_transactions(user_id, plaid_access_token):
        log_error(
            "load_transactions()",
            "could not load recent transactions ",
        )
        abort(400)

    return ("OK", 200)


@functions_framework.http
@auth
def plaid(request):
    if request.method == "POST":
        return plaid_link(request)
    elif request.method == "GET":
        return load_transactions(request)

    abort(405)
