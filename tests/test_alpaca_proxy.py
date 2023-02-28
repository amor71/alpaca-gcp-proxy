import requests

base_url: str = "http://localhost:8080/proxy/alpaca"

account_json = {
    "enabled_assets": ["us_equity", "crypto"],
    "contact": {
        "email_address": "cool_alpaca8@example.com",
        "phone_number": "555-666-7788",
        "street_address": ["20 N San Mateo Dr"],
        "unit": "Apt 1A",
        "city": "San Mateo",
        "state": "CA",
        "postal_code": "94401",
        "country": "USA",
    },
    "identity": {
        "given_name": "Johnny",
        "middle_name": "Smith",
        "family_name": "Doe",
        "date_of_birth": "1990-01-01",
        "tax_id": "666-55-4321",
        "tax_id_type": "USA_SSN",
        "country_of_citizenship": "USA",
        "country_of_birth": "USA",
        "country_of_tax_residence": "USA",
        "funding_source": ["employment_income"],
    },
    "disclosures": {
        "is_control_person": False,
        "is_affiliated_exchange_or_finra": True,
        "is_politically_exposed": False,
        "immediate_family_exposed": False,
        "context": [
            {
                "context_type": "AFFILIATE_FIRM",
                "company_name": "Finra",
                "company_street_address": ["1735 K Street, NW"],
                "company_city": "Washington",
                "company_state": "DC",
                "company_country": "USA",
                "company_compliance_email": "compliance@finra.org",
            }
        ],
    },
    "agreements": [
        {
            "agreement": "customer_agreement",
            "signed_at": "2020-09-11T18:13:44Z",
            "ip_address": "185.13.21.99",
            "revision": "19.2022.02",
        },
        {
            "agreement": "crypto_agreement",
            "signed_at": "2020-09-11T18:13:44Z",
            "ip_address": "185.13.21.99",
            "revision": "04.2021.10",
        },
    ],
    "documents": [
        {
            "document_type": "identity_verification",
            "document_sub_type": "passport",
            "content": "/9j/Cg==",
            "mime_type": "image/jpeg",
        }
    ],
    "trusted_contact": {
        "given_name": "Jane",
        "family_name": "Doe",
        "email_address": "jane.doe@example.com",
    },
}


def test_proxy_post_w_payload():
    url = f"{base_url}/v1/accounts"

    r = requests.post(url=url, json=account_json)

    print(r)
    print(r.json())

    assert r.status_code == 409, "expected success"


def test_proxy_post_wo_payload():
    url = f"{base_url}/v1/accounts/11111"

    r = requests.get(url=url)

    print(r)
    print(r.json())

    assert r.status_code == 422, "expected failure"
