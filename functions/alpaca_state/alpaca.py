import time

from google.cloud import firestore  # type: ignore
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import \
    CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource


def alpaca_state_handler(user_id: str, payload: dict):
    print(f"email={user_id}, payload={payload}")

    db = firestore.Client()

    doc_ref = db.collection("users").document(user_id)

    update_data = {
        "alpaca_account_id": payload.get("id"),
        "updated": time.time_ns(),
    }

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type
    status = doc_ref.update(update_data)

    print("document update status=", status)
