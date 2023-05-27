import functions_framework


@functions_framework.http
def slackbot(request):
    """Implement POST /v1/slackbot"""

    # Validate inputs
    payload = request.get_json() if request.is_json else None

    print("payload", payload)
    return (payload["challenge"], 200)
