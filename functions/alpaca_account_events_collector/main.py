import datetime
import json
from zoneinfo import ZoneInfo

import functions_framework
from cloudevents.http.event import CloudEvent

from infra.alpaca_action import process_account_update
from infra.data.alpaca_events import AlpacaEvents
from infra.logger import log_error
from infra.proxies.alpaca import alpaca_proxy


def process_from_event(event_id: str):
    EDT = ZoneInfo("US/Eastern")
    now_in_nyc = datetime.datetime.now(EDT)
    args = {"since_id": event_id, "until": now_in_nyc.isoformat()}
    r = alpaca_proxy(
        method="GET",
        url="/v1/events/accounts/status",
        args=args,
        payload=None,
        headers={"accept": "text/event-stream"},
        stream=True,
    )

    if r.status_code != 200:
        log_error(
            "process_from_event()", f"failed with {r.status_code} & {r.text}"
        )
        return

    print("events_listener(): stream started")
    if r.encoding is None:
        r.encoding = "utf-8"

    for line in r.iter_lines(decode_unicode=True):
        if line and line[:6] == "data: ":
            payload = json.loads(line[6:])
            print(f"events_listener() received update {payload}")
            process_account_update(payload)


@functions_framework.cloud_event
def alpaca_account_events_collector(cloud_event: CloudEvent):
    print("alpaca_account_events_collector()")

    if not (data := AlpacaEvents.latest_event_id("accounts")):
        log_error("alpaca_account_events_collector()", "no events")
        return

    if not (event_id := data.get("event_id")):
        log_error(
            "alpaca_account_events_collector()",
            f"can't get event_id in {data}",
        )
        return

    process_from_event(event_id=event_id)
