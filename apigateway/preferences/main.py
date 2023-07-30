import functions_framework
from flask import abort

from infra import auth, authenticated_user_id  # type: ignore
from infra.data.preferences import Preferences
from infra.logger import log_error


@functions_framework.http
@auth
def preferences(request):
    """Implement PATCH /v1/users/preferences -> update preferences"""

    payload = request.get_json() if request.is_json else None

    if not payload:
        abort(400)

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("handle_post", "could not load authenticated user_id")
        abort(400)

    Preferences.add(user_id, payload)

    return ("OK", 200)
