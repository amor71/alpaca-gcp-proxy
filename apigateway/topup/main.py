import functions_framework

from infra import auth  # type: ignore


@functions_framework.http
@auth
def topup(request):
    user_id = request.args.get("userId")

    print(request)

    # Use the user_id parameter in your function logic
    if user_id:
        # Do something with the user_id
        print(f"Received user_id: {user_id}")

    return ("OK", 200)
