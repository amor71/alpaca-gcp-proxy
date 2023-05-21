import functions_framework

from infra import auth  # type: ignore


@functions_framework.http
@auth
def topup(request):
    print("topup", request)
    return ("OK", 200)
