import time

import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore


def get_model_portfolio_by_name(name: str) -> dict | None:
    """Look-up a portfolio by portfolio name"""

    r = alpaca_proxy(
        method="GET",
        url="/v1/beta/rebalancing/portfolios",
        args=None,
        payload=None,
        headers=None,
    )

    if r.status_code != 200:
        return None

    portfolios = r.json()
    return next(
        (
            portfolio
            for portfolio in portfolios
            if portfolio["name"].lower() == name.lower()
            and portfolio["status"] == "active"
        ),
        None,
    )


def load_account_id(user_id: str) -> str | None:
    """Load account-id from Firestore, based on the user-id"""

    db = firestore.Client()
    doc_ref = db.collection("users").document(user_id)

    if not (doc := doc_ref.get()):
        log_error("load_account_id", f"could not load {user_id} document")
        return None

    print(f"loaded document:{doc}")
    if not (alpaca_account_id := doc.get("alpaca_account_id")):
        log_error(
            "load_account_id",
            f"{user_id} does not have 'alpaca_account_id' property",
        )
        return None

    return alpaca_account_id


def save_new_mission(user_id: str, mission_name: str, strategy: str) -> str:
    db = firestore.Client()

    doc_ref = (
        db.collection("missions")
        .document(user_id)
        .collection("user_missions")
        .document()
    )
    data = {
        "name": mission_name,
        "strategy": strategy,
        "created": time.time_ns(),
    }

    status = doc_ref.set(data)

    print("document update status=", status)

    return status


def create_run(user_id: str, model_portfolio: dict) -> str | None:
    """rebalance user account, to bring it to same allocations as in the model portfolio"""

    if not (user_account_id := load_account_id(user_id)):
        return None

    # TODO: Do we need anything except weights?
    rebalance_payload: dict = {
        "account_id": user_account_id,
        "type": "full_rebalance",
        "weights": model_portfolio["weights"],
    }

    r = alpaca_proxy(
        method="POST",
        url="/v1/beta/rebalancing/runs",
        payload=rebalance_payload,
    )

    if r.status_code != 200:
        log_error(
            "create_run",
            f"run failed status code {r.status_code} and {r.text}",
        )
        return None

    run_payload = r.json()

    return run_payload.id


def handle_post(request):
    payload = request.get_json() if request.is_json else None

    if (
        not payload
        or not (name := payload.get("name"))
        or not (strategy := payload.get("strategy"))
    ):
        if payload:
            log_error("handle_post", f"payload={payload}")
        return ("Missing or invalid payload", 400)

    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error("handle_post", "could not load authenticated user_id")
        return None

    if not (model_portfolio := get_model_portfolio_by_name(strategy)):
        return (f"model portfolio '{strategy}' not found", 400)

    print(
        f"Located portfolio id {model_portfolio['id']} for strategy name {strategy}"
    )

    create_run(model_portfolio)

    mission_id, created = save_new_mission(user_id, name, strategy)

    # track_run(run_id)

    return ({"id": mission_id, "status": "created", "created": created}, 200)


@functions_framework.http
@auth
def missions(request):
    """Implement /v1/missions"""

    if request.method == "POST":
        return handle_post(request)

    return (f"{request.method} not yet implemented", 405)
