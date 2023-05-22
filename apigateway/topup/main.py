from enum import Enum

import functions_framework

from infra import auth  # type: ignore


class Frequency(Enum):
    Weekly = 1
    Monthly = 2


def process(amount: int, frequency: Frequency) -> None:
    print(f"process: {amount}, {frequency}")


@functions_framework.http
@auth
def topup(request):
    """Implement PUT /users/{userId}/topup end-point"""

    user_id = request.args.get("userId")
    print(f"Received user_id: {user_id}")

    # validate API
    payload = request.get_json() if request.is_json else None

    if (
        not payload
        or not (amount_str := payload.get("amount"))
        or not (frequency_str := payload.get("frequency"))
    ):
        return (
            "Missing or invalid payload (expected JSON w/ 'amount' and 'frequency')",
            400,
        )

    try:
        amount = int(amount_str)
        assert amount > 0
    except Exception:
        return ("amount needs to be positive int", 400)

    try:
        frequency = Frequency[frequency_str]
    except Exception:
        return ("frequency needs to be 'Weekly' or 'Monthly'", 400)

    process(amount, frequency)

    return ("OK", 200)
