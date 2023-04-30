import functions_framework

from .new_user import new_user_handler


@functions_framework.http
def new_user(request):
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    payload = request.get_json() if request.is_json else None

    if (
        not payload
        or not (user_id := payload.get("user_id"))
        or not (email_id := payload.get("email_id"))
    ):
        return ("Missing or invalid payload", 400)

    new_user_handler(user_id, email_id)

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return ("OK", 200, headers)
