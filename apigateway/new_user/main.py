import functions_framework

from infra import auth  # type: ignore

from .new_user import new_user_handler


@functions_framework.http
@auth
def new_user(request):
    payload = request.get_json() if request.is_json else None

    if (
        not payload
        or not (user_id := payload.get("user_id"))
        or not (email_id := payload.get("email_id"))
    ):
        return ("Missing or invalid payload", 400)

    new_user_handler(user_id, email_id)
    return ("OK", 200)
