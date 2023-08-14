import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.proxies.plaid import plaid_proxy
from infra.stytch_actions import update_user_vault


def plaid_link(request):
    if not (public_token := request.args.get("publicToken")):
        log_error("plaid_link()", "can not get argument")
        abort(400)

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("handle_post", "could not load authenticated user_id")
        abort(400)

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
        headers={"Content-Type": "application/json"},
        args=None,
    )
    if r.status_code != 200:
        log_error(
            "plaid_link()",
            f"failed call to Plaid with {r.status_code}:{r.text}",
        )
        abort(400)

    plaid_payload = r.json()
    if not (plaid_access_token := plaid_payload.get("access_token")):
        log_error("plaid_link()", "failed to get access_token")

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
