import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error


def plaid_link(request):
    return ("OK", 200)


@functions_framework.http
@auth
def plaid(request):
    """Implement  /v1/missions/plaid"""

    if request.method == "POST":
        return plaid_link(request)

    abort(405)
