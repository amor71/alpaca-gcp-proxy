import requests

base_url: str = "https://api.nine30.com/link"


def no_test_link_missing_parameter() -> None:
    url = f"{base_url}"

    r = requests.post(url=url)
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"


def no_test_link_wrong_parameter() -> None:
    url = f"{base_url}"

    r = requests.post(url=url, json={"public_token": 100})
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"


def test_link_happy_parameter() -> None:
    url = f"{base_url}"

    r = requests.post(
        url=url,
        json={
            "public_token": "public-sandbox-5be22dbe-4adb-4709-a65b-a83b88d8801f",
            "alpaca_account_id": "2cf894e5-38d2-4399-b50d-2b80b745a5e4",
            "plaid_account_id": "5pjKDJwkRbHL1XB7zLp3hlML3a8Epdf38jvlw",
        },
    )
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"
