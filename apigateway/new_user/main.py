import functions_framework
from new_user import new_user_handler

from infra import auth  # type: ignore
from infra.logger import log_error


@functions_framework.http
@auth
def new_user(request):
    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "new_user()",
            "could not load authenticated user_id, this shouldn't have happened",
        )
        return ("Something went wrong", 403)

    new_user_handler(user_id)
    return ("OK", 200)
