import requests

base_url: str = "http://localhost:8080/link"


def test_link_missing_parameter() -> None:
    url = f"{base_url}"

    r = requests.post(url=url)
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"


def test_link_wrong_parameter() -> None:
    url = f"{base_url}"

    r = requests.post(url=url, json={"public_token": 100})
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"
