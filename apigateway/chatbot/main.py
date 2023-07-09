import json

import functions_framework
import openai
from google.cloud import secretmanager  # type:ignore

from infra import auth, authenticated_user_id  # type:ignore
from infra.config import project_id  # type:ignore
from infra.data.chats import save_chat  # type:ignore
from infra.proxies.proxy_base import check_crc  # type:ignore

api_key = "openai_api_key"
org_id = "openai_org_id"


def _get_credentials() -> tuple:
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    api_key_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{api_key}/versions/latest"
        }
    )
    org_id_response = client.access_secret_version(
        request={
            "name": f"projects/{project_id}/secrets/{org_id}/versions/latest"
        }
    )

    check_crc(api_key_response)
    check_crc(org_id_response)
    return (
        api_key_response.payload.data.decode("UTF-8"),
        org_id_response.payload.data.decode("UTF-8"),
    )


def _get_portfolio_details() -> str:
    """Return portfolio composition for a specific user"""
    portfolio_composition = {
        "AAPL": 10,
        "TSLA": 5,
        "NVDA": 10,
        "SPY": 3,
        "GLD": 3,
    }

    return json.dumps(portfolio_composition)


@functions_framework.http
@auth
def chatbot(request):
    """Implement POST /v1/chatbot"""

    # Validate inputs
    payload = request.get_json() if request.is_json else None

    if not payload or not (question := payload.get("question")):
        return ("Missing or invalid payload", 400)

    request_session_id = payload.get("sessionId")
    request_session_id = (
        str(request_session_id) if request_session_id else request_session_id
    )
    openai.api_key, openai.organization = _get_credentials()
    user_id = authenticated_user_id.get()  # type: ignore
    print(f"chatbot request for user_id={user_id}")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. You answer questions as a 25 year old financial professional. You are funny, but never sarcastic. You are using a voice and language that fits young people ages 18 to 26 years old.",
        },
        # {"assistant": "\n\nI'm Hushi, how may I assist you today?"},
        {"role": "user", "content": f"{question}"},
    ]
    functions = [
        {
            "name": "get_portfolio_details",
            "description": "Get the list of equities in my portfolio",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
    ]

    chat_completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=functions,
        function_call="auto",
        user=user_id,
    )

    print(chat_completion)

    response_message = chat_completion["choices"][0]["message"]

    if response_message.get("function_call"):
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_portfolio_details": _get_portfolio_details,
        }  # only one function in this example, but you can have multiple
        function_name = response_message["function_call"]["name"]
        function_to_call = available_functions[function_name]
        # function_args = json.loads(response_message["function_call"]["arguments"])

        function_response = function_to_call()

        print(f"function response: {function_response}")

        # Step 4: send the info on the function call and function response to GPT
        messages.append(
            response_message
        )  # extend conversation with assistant's reply
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            user=user_id,
        )  # get a new response from GPT where it can see the function response

        print(f"second response {second_response}")
        answer = second_response["choices"][0]["message"].content

    else:
        answer = response_message.content

    session_id = save_chat(
        user_id=user_id,
        question=question,
        answer=answer,
        id=request_session_id,
    )
    payload: dict = {"sessionId": session_id, "answer": answer}

    return (payload, 200)
