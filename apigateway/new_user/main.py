import functions_framework
from new_user import new_user_handler

from infra import auth  # type: ignore


@functions_framework.http
@auth
def new_user(request):
    new_user_handler(user_id)
    return ("OK", 200)
