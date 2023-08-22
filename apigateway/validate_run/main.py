import functions_framework
from flask import Request, abort
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from infra.alpaca_action import get_available_cash, get_model_portfolio_by_name
from infra.config import location, project_id, rebalance_queue  # type: ignore
from infra.data.missions import Missions, Runs
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy  # type: ignore
from infra.stytch_actions import get_alpaca_account_id


def handle_validate_run(request: Request):
    # validate API
    if not (user_id := request.args.get("runId")):
        log_error("handle_users_topup()", "missing runId")
        abort(400)

    return ("OK", 200)


@functions_framework.http
def validate_run(request):
    """Implement /v1/missions/validate/{runId} end points"""

    if request.method == "PATCH":
        return handle_validate_run(request)

    return (f"{request.method} not yet implemented", 405)
