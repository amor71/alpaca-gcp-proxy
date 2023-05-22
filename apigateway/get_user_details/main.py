import functions_framework

from infra import auth  # type: ignore


@functions_framework.http
@auth
def get_user_details(request):
    return ("OK", 200)
