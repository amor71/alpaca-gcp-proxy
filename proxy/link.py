from flask import Request
from requests import HTTPError, Response

from infra.proxies.alpaca import alpaca_proxy
from infra.proxies.plaid import plaid_proxy


# TODO: Remove Print Logs
def link(request: Request, headers: dict) -> Response:
    print(request)

    args = list(request.args.items())

    try:
        payload = request.get_json()
        public_token: str = payload["public_token"]
        if not public_token:
            raise HTTPError("public_token can't be null")
        alpaca_account_id: str = payload["alpaca_account_id"]
        if not alpaca_account_id:
            raise HTTPError("alpaca_account_id can't be null")
        plaid_account_id: str = payload["plaid_account_id"]
        if not plaid_account_id:
            raise HTTPError("plaid_account_id can't be null")
    except Exception as e:
        raise HTTPError(
            "JSON body must include 'public_token' and 'account_id"
        ) from e

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
        headers=headers,
    )
    print(f"response 1 {r} {r.json()}")
    if r.status_code != 200:
        return r

    r = plaid_proxy(
        method="POST",
        url="/processor/token/create",
        payload={
            "access_token": r.json()["access_token"],
            "processor": "alpaca",
            "account_id": plaid_account_id,
        },
        headers=headers,
    )

    print(f"response 2 {r} {r.json()}")
    if r.status_code == 400:
        return r

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{alpaca_account_id}/ach_relationships",
        payload={"processor_token": r.json()["processor_token"]},
        args=args,
        headers=headers,
    )

    print(f"response 3 {r} {r.json()}")
    return r
