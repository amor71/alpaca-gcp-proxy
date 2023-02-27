import requests

base_url:str ="http://localhost:8080"

def test_negative_proxy():
    url = f"{base_url}/no_proxy"
    r = requests.get(url)

    assert r.status_code == 400, "expected HTTP error 400"
