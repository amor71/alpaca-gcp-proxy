import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.alpaca_action import get_account_balance
from infra.data.missions import Mission, Missions
from infra.logger import log_error
from infra.stytch_actions import get_alpaca_account_id


def process_mission(account_balance: int, mission_details: Mission) -> dict:
    """create mission payload"""

    payload: dict = {
        "initialAmount": mission_details.data["initial_amount"],
        "weeklyTopup": mission_details.data["weekly_topup"],
        "forecast": mission_details.forecaster(),
        "name": mission_details.data["name"],
        "strategy": mission_details.data["strategy"],
        "milestones": mission_details.calculate_milestones(account_balance),
        "currentBalance": account_balance,
    }

    return payload


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
        abort(403)

    if not (alpaca_account_id := get_alpaca_account_id(user_id)):
        log_error("get_missions()", "alpaca account not ready")
        abort(400)

    # TODO: account balance is not per mission!
    if not (account_balance := get_account_balance(alpaca_account_id)):
        abort(400)

    missions = Missions(user_id=user_id)
    payload = [
        process_mission(account_balance, mission) for mission in missions
    ]
    if not payload:
        log_error(
            "get_missions()", f"{user_id} does not have any active missions"
        )
        abort(400)

    return (payload, 200)
