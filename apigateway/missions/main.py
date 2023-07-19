import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth  # type: ignore


@functions_framework.http
@auth
def missions(request):
    return ("it's all good", 200)
