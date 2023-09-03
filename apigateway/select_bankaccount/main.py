import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.users import User
from infra.logger import log_error


@functions_framework.http
@auth
def select_bankaccount(request):
    """implement PUT /v1/plaid/account/{accountId}"""

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "select_bankaccount()",
            "could not load authenticated user_id, this shouldn't have happened",
        )
        abort(403)

    if not (account_id := request.args.get("accountId")):
        log_error("select_bankaccount()", "missing accountId")
        abort(400)

    User.update(user_id=user_id, payload={"plaid_account_id": account_id})

    return ("OK", 200)
