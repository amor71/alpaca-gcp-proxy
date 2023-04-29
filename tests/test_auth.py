from auth import is_token_invalid


def test_authenticate():
    token = "session-test-0419f098-120f-4906-9f56-c66161e1f383"

    result = is_token_invalid(token=token)

    print(result)
