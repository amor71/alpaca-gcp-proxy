import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.past_transactions import save_past_transactions
from infra.logger import log_error
from infra.plaid_actions import get_access_token, get_recent_transactions
from infra.stytch_actions import get_from_user_vault, update_user_vault


@functions_framework.http
def plaid_callback(request):
    """Implementation POST"""
    if request.method != "POST":
        abort(405)

    payload = request.get_json() if request.is_json else None

    print(f"payload = {payload} from {request.remote_addr}")

    return ("OK", 200)
