import functions_framework

from infra import auth  # type: ignore


@functions_framework.http
@auth
def chatbot(request):
    """Implement POST /v1/chatbot"""

    return ("OK", 200)
