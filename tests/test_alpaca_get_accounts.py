import json

import requests

base_url: str = "http://localhost:8080/alpaca"


def test_get_accounts():
    url = f"{base_url}/v1/accounts"

    r = requests.get(url=url)

    print(r, r.reason)
    print(json.dumps(r.json(), indent=4))

    assert r.status_code == 200, "expected success"


def test_get_accounts_w_parameters():
    url = f"{base_url}/v1/accounts?created_before=2019-10-12T07:20:50.52Z"

    r = requests.get(url=url)

    print(r, r.reason)
    print(json.dumps(r.json(), indent=4))

    assert r.status_code == 200, "expected success"
