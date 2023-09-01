import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.missions import Missions
from infra.logger import log_error


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

    payload = []
    for mission in missions:
        print(mission)

    if not payload:
        log_error(
            "get_missions()", f"{user_id} does not have any active missions"
        )
        abort(400)

    return ("OK", 200)
