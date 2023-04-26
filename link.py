from alpaca import alpaca_proxy
from plaid import plaid_proxy


# TODO: Remove Print Logs
def link(request):
    print(request)

    args = list(request.args.items())

    try:
        payload = request.get_json()
        public_token = payload["public_token"]
        alpaca_account_id = payload["alpaca_account_id"]
        plaid_account_id = payload["plaid_account_id"]
    except Exception:
        return ("JSON body must include 'public_token' and 'account_id", 400)

    r = plaid_proxy(
        method="POST",
        url="/item/public_token/exchange",
        payload={"public_token": public_token},
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
    )

    print(f"response 2 {r} {r.json()}")
    if r.status_code == 400:
        return r

    r = alpaca_proxy(
        method="POST",
        url=f"/v1/accounts/{alpaca_account_id}/ach_relationships",
        payload={"processor_token": r.json()["processor_token"]},
        args=args,
    )

    print(f"response 3 {r} {r.json()}")
    return r
