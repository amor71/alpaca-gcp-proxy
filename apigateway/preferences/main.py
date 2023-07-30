import functions_framework

from infra import auth, authenticated_user_id  # type: ignore


@functions_framework.http
@auth
def missions(request):
    """Implement PATCH /v1/users -> update preferences"""
