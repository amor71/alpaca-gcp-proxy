import functions_framework
import telemetrics
from flask import Request, abort

from infra.alpaca_action import get_available_cash, get_model_portfolio_by_name
from infra.data.missions import Missions, Runs
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore
from infra.stytch_actions import get_alpaca_account_id


def save_run(
    user_id: str,
    run_id: str,
    mission_name: str,
    strategy: str,
) -> None:
    Runs.add(run_id, user_id, mission_name, strategy)


# TODO: move to infra and consolidate w/ mission end-point
def create_run(alpaca_account_id: str, model_portfolio: dict) -> str | None:
    """rebalance user account, to bring it to same allocations as in the model portfolio"""

    cash = get_available_cash(alpaca_account_id)
    if not cash:
        log_error(
            "create_run()", "account can't be used for trading at the moment"
        )
        return None
    elif cash < 1.0:
        log_error(
            "create_run()", f"account balance {cash} too low for trading"
        )
        return None

    # TODO: Do we need anything except weights?
    rebalance_payload: dict = {
        "account_id": alpaca_account_id,
        "type": "full_rebalance",
        "weights": model_portfolio["weights"],
    }

    r = alpaca_proxy(
        method="POST",
        url="/v1/beta/rebalancing/runs",
        payload=rebalance_payload,
        args=None,
        headers=None,
    )

    if r.status_code != 200:
        log_error(
            "create_run",
            f"run failed status code {r.status_code} and {r.text}",
        )

        return "reschedule" if r.status_code == 422 else None

    run_payload = r.json()
    return run_payload["id"]


def handle_create_rebalance(request: Request):
    # validate API
    if not (user_id := request.args.get("userId")):
        log_error("handle_users_topup()", "missing user_id")
        abort(400)

    missions = Missions(user_id)

    for mission in missions:
        strategy = mission.get("strategy")
        if not (model_portfolio := get_model_portfolio_by_name(strategy)):
            log_error(
                "handle_create_rebalance()",
                f"model portfolio '{strategy}' not found",
            )
            return ("invalid strategy", 202)

        if not (alpaca_account_id := get_alpaca_account_id(user_id)):
            log_error(
                "handle_create_rebalance()",
                f"user_id {user_id} does not have alpaca_account_id (yet)",
            )
            return ("invalid_user", 202)

        if not (run_id := create_run(alpaca_account_id, model_portfolio)):
            return ("failed run", 201)

        save_run(
            user_id=user_id,
            run_id=run_id,
            mission_name=mission.name,
            strategy=mission.get("strategy"),
        )

    return ("OK", 200)


@functions_framework.http
def missions(request):
    """Implement /v1/missions/rebalance/{userId} end points"""

    if request.method == "POST":
        return handle_create_rebalance(request)

    return (f"{request.method} not yet implemented", 405)
