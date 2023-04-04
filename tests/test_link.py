import requests

base_url: str = "http://localhost:8080/proxy/link"


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
            "public_token": "public-sandbox-22c9bf9c-3296-46a7-946e-ac9f49a1b3aa",
            "account_id": "61469dbb-21f0-427b-81eb-da5b14c56a10",
        },
    )
    print(r.status_code)

    assert r.status_code == 400, "expect HTTP 400"
