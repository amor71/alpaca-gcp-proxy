from google.cloud import firestore  # type: ignore
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import \
    CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

metrics.set_meter_provider(
    MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                CloudMonitoringMetricsExporter(), export_interval_millis=5000
            )
        ],
        resource=Resource.create(
            {
                "service.name": "KPI",
                "service.namespace": "users",
                "service.instance.id": "instance123",
            }
        ),
    )
)
meter = metrics.get_meter(__name__)


def add_new_alpaca_application():
    counter = meter.create_counter(
        name="alpaca_application",
        description="New Alpaca Application",
        unit="1",
    )

    staging_labels = {"environment": "development"}
    counter.add(1, staging_labels)


def alpaca_state_handler(email_id: str, payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    doc_ref = db.collection("users").document(email_id)

    update_data = {"alpaca_account_id": payload.get("id")}

    if status := payload.get("status"):
        update_data["alpaca_status"] = status
    if crypto_status := payload.get("crypto_status"):
        update_data["alpaca_crypto_status"] = crypto_status
    if account_type := payload.get("account_type"):
        update_data["alpaca_account_type"] = account_type
    status = doc_ref.update(update_data)

    print("document update status=", status)
