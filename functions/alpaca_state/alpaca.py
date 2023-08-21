import json
from concurrent import futures

from google.cloud import firestore  # type: ignore
from google.cloud import pubsub_v1  # type:ignore

from infra.config import post_ach_link_topic_id, project_id
from infra.data.alpaca_account import AlpacaAccount
from infra.data.alpaca_events import AlpacaEvents
from infra.data.bank_account import Account
from infra.data.users import User
from infra.logger import log_error
from infra.plaid_actions import create_alpaca_link
from infra.proxies.alpaca import alpaca_proxy
from infra.stytch_actions import get_from_user_vault, update_user_vault


# TODO: consider converting into workflow
def process_account_update(payload):
    # get user-id from account_number
    account_number = payload.get("account_number")
    user_id = AlpacaAccount.load(account_number)

    if not user_id:
        log_error("process_account_update()", "can't load user_id")
        return

    if not (alpaca_account_id := payload.get("account_id")):
        log_error(
            "process_account_update()",
            f"payload {payload} does not have account_id",
        )
        return

    # TODO: consider handling crypto account approvals too
    if payload.get("status_to") == "ACTIVE":
        User.update(user_id, {"onboardingCompleted": True})
        handle_alpaca_activated(user_id, alpaca_account_id)

    # Update user record
    User.update(user_id, payload)
    User.update(user_id, {"alpaca": True})

    # Store event-id = mark event as processed
    AlpacaEvents.add("accounts", payload.get("event_id"))


def handle_alpaca_activated(user_id, alpaca_account_id):
    # Get Plaid access token
    if not (
        plaid_access_token := get_from_user_vault(
            user_id, "plaid_access_token"
        )
    ):
        log_error(
            "handle_alpaca_activated()",
            f"failed to get plaid_access_token for {user_id}",
        )
        return

    # Get user account-id from DB
    account_ids = Account.get_account_ids(user_id)

    if not account_ids:
        log_error(
            "handle_alpaca_activated()",
            f"failed to load account-id for user {user_id}",
        )
        return

    # Create plaid alpaca link
    ach_relationship_id = create_alpaca_link(
        plaid_access_token, account_ids[0], alpaca_account_id
    )

    # Store relationship-id
    update_user_vault(user_id, "relationship_id", ach_relationship_id)

    trigger_post_ach_link(user_id)


def trigger_post_ach_link(user_id: str):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, post_ach_link_topic_id)
    publish_future = publisher.publish(
        topic_path,
        json.dumps({"user_id": user_id}).encode("utf-8"),
    )

    futures.wait([publish_future])
    print("triggered post_ach_link function")


def events_listener():
    r = alpaca_proxy(
        method="GET",
        url="/v1/events/accounts/status",
        args=None,
        payload=None,
        headers={"accept": "text/event-stream"},
        stream=True,
    )

    if r.status_code == 200:
        print("events_listener(): stream started")
        if r.encoding is None:
            r.encoding = "utf-8"

        for line in r.iter_lines(decode_unicode=True):
            if line and line[:6] == "data: ":
                payload = json.loads(line[6:])
                print(f"events_listener() received update {payload}")
                process_account_update(payload)


def alpaca_state_handler(user_id: str, payload: dict):
    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    update_data = {
        "alpaca_updated": firestore.SERVER_TIMESTAMP,
    }

    if alpaca_account_id := payload.get("id"):
        update_user_vault(user_id, "alpaca_account_id", alpaca_account_id)
    if relationship_id := payload.get("relationship_id"):
        update_user_vault(user_id, "relationship_id", relationship_id)
    if account_number := payload.get("account_number"):
        AlpacaAccount.save(account_number, user_id)

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type

    if doc_ref.get().exists:
        status = doc_ref.update(update_data)
    else:
        status = doc_ref.set(update_data)
