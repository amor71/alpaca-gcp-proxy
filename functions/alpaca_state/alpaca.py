from datetime import datetime, timezone

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


def alpaca_state_handler(payload: dict):
    print("payload=", payload)

    db = firestore.Client()

    doc_ref = db.collection("users").document(payload["email_id"])
    status = doc_ref.set(
        {
            "user_id": payload["user_id"],
            "state": 1,
            "modified_at": datetime.now(timezone.utc),
        }
    )

    add_new_alpaca_application()
    print("document write status=", status)
