import functions_framework
from flask import abort

from infra.data.plaid_item import PlaidItem
from infra.logger import log_error
from infra.plaid_actions import load_recent_transactions
from infra.stytch_actions import get_from_user_vault


@functions_framework.http
def plaid_callback(request):
    """Implementation POST"""
    if request.method != "POST":
        abort(405)

    originator_ip = request.headers.get("X-Forwarded-For").split(",")[0]

    if originator_ip not in {
        "52.21.26.131",
        "52.21.47.157",
        "52.41.247.19",
        "52.88.82.239",
    }:
        log_error("plaid_callback", "not originated from Plaid servers!")

    payload = request.get_json() if request.is_json else None

    if payload.get("webhook_type") == "TRANSACTIONS":
        print(f"TRANSACTIONS callback {payload.get('webhook_code')}")

        item_id = payload.get("item_id")
        user_id = PlaidItem.load(item_id)

        print(f"item_id={item_id} -> user_id={user_id}")

        plaid_access_token = get_from_user_vault(
            user_id=user_id, key="plaid_access_token"
        )

        if not load_recent_transactions(user_id, plaid_access_token):
            log_error(
                "load_transactions()",
                "could not load recent transactions ",
            )
            abort(400)

    return ("OK", 200)
