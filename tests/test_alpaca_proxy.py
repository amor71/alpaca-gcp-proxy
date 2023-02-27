import requests

base_url: str = "http://localhost:8080/proxy/alpaca"


def test_proxy_post_w_payload():
    url = f"{base_url}/v1/account"

    r = requests.post(url=url, json={"first_name": "John", "last_name": "Doe"})

    assert r.status_code == 200, "expected success!"
