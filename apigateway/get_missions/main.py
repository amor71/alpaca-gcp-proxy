import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.missions import Mission, Missions
from infra.logger import log_error


def process_mission(mission_details: Mission) -> dict:
    """create mission payload"""

    payload: dict = {
        "initialAmount": mission_details.data["initial_amount"],
        "weeklyTopup": mission_details.data["weekly_topup"],
        "forecast": mission_details.forecaster(),
        "name": mission_details.data["name"],
        "strategy": mission_details.data["strategy"],
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
        return ("Something went wrong", 403)

    missions = Missions(user_id=user_id)
    payload = [process_mission(mission) for mission in missions]
    if not payload:
        log_error(
            "get_missions()", f"{user_id} does not have any active missions"
        )
        abort(400)

    return (payload, 200)
