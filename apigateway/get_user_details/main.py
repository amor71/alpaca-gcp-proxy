import functions_framework
from google.cloud import firestore  # type: ignore

from infra import auth, authenticated_user_id  # type: ignore
from infra.logger import log_error
from infra.plaid_actions import load_identities
from infra.stytch_actions import get_from_user_vault


def _process_owner_data(data: dict, owner: dict):
    if names := owner.get("names"):
        print(f"names {names}")
        data["names"] += names
    if phone_numbers := owner.get("phone_numbers"):
        print(f"phone_numbers {phone_numbers}")
        data["phone_numbers"] += phone_numbers
    if addresses := owner.get("addresses"):
        print(f"addresses {addresses}")
        data["addresses"] += addresses
    if emails := owner.get("emails"):
        print(f"emails {emails}")
        data["emails"] += emails


def _process_identities(plaid_access_token: str, data: dict) -> dict:
    data["names"] = []
    data["phone_numbers"] = []
    data["addresses"] = []
    data["emails"] = []

    if identities := load_identities(plaid_access_token):
        for identity in identities:
            if owners := identity.get("owners"):
                for owner in owners:
                    _process_owner_data(data, owner)

    data["names"] = list(set(data["names"]))
    data["phone_numbers"] = [
        dict(t) for t in {tuple(d.items()) for d in data["phone_numbers"]}
    ]
    return data


def process(user_id: str) -> dict | None:
    db = firestore.Client()

    document_ref = db.collection("users").document(user_id)
    doc = document_ref.get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    if not (
        plaid_access_token := get_from_user_vault(
            user_id=user_id, key="plaid_access_token"
        )
    ):
        print("process(): plaid account not setup")
        return data

    return _process_identities(plaid_access_token, data)


@functions_framework.http
@auth
def get_user_details(request):
    user_id = authenticated_user_id.get()  # type: ignore
    if not user_id:
        log_error(
            "new_user()",
            "could not load authenticated user_id, this shouldn't have happened",
        )
        return ("Something went wrong", 403)

    # TODO: Validate email belong to authenticated user

    payload = process(user_id)

    return (payload, 200) if payload else ("user does not exist", 404)
