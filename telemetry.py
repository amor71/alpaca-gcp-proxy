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


def add_new_user_counter():
    # Creates metric workload.googleapis.com/request_counter with monitored resource generic_task
    counter = meter.create_counter(
        name="new_users",
        description="number of users",
        unit="1",
    )

    staging_labels = {"environment": "development"}
    counter.add(1, staging_labels)


def add_new_alpaca_application():
    counter = meter.create_counter(
        name="alpaca_application",
        description="New Alpaca Application",
        unit="1",
    )

    staging_labels = {"environment": "development"}
    counter.add(1, staging_labels)
