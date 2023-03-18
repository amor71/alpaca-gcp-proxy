import requests

base_url: str = "http://localhost:8080/stytch"

account_json = {"email": "amichay@nine30.com"}


def test_stytch():
    url = f"{base_url}/magic_links/email/login_or_create"

    r = requests.post(url=url, json=account_json)

    print(r)
    print(r.json())

    assert r.status_code == 200, "expected success"
