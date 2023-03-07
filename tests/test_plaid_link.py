import requests

base_url: str = "http://localhost:8080/plaid"


def test_proxy_no_route():
    url = f"{base_url}"

    r = requests.post(url=url)
    assert r.status_code == 400, "expected HTTP 400"
    print(r)


def test_proxy_create_link():
    url = f"{base_url}/link/token/create"

    r = requests.post(
        url=url,
        json={
            "client_name": "pytest",
            "language": "en",
            "country_codes": ["US"],
            "products": ["auth"],
            "user": {
                "client_user_id": "mememe",
            },
            "account_filters": {
                "depository": {"account_subtypes": ["checking"]}
            },
        },
    )
    assert r.status_code == 200, "expected HTTP 200"
    print(r, r.json())


def test_negative_proxy_create_link():
    url = f"{base_url}/link/token/create"

    r = requests.post(
        url=url,
        json={
            "client_name": "pytest",
            "language": "en",
            "country_codes": ["US"],
            "products": ["auth"],
            "account_filters": {
                "depository": {"account_subtypes": ["checking"]}
            },
        },
    )
    assert r.status_code == 400, "expected HTTP 400"
    print(r, r.json())
