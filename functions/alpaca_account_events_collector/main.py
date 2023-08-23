import functions_framework
from cloudevents.http.event import CloudEvent

from infra.data.alpaca_events import AlpacaEvents


@functions_framework.cloud_event
def alpaca_account_events_collector(cloud_event: CloudEvent):
    print("alpaca_account_events_collector()")

    data = AlpacaEvents.latest_event_id("accounts")

    print("data=", data)
