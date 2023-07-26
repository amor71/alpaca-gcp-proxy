from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import \
    CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

counters: dict = {}
metrics.set_meter_provider(
    MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                CloudMonitoringMetricsExporter(add_unique_identifier=True),
                export_interval_millis=5000,
            )
        ],
        resource=Resource.create(
            {
                "service.name": "hush",
                "service.namespace": "runs",
                "service.instance.id": "instance123",
            }
        ),
    )
)
meter = metrics.get_meter(__name__)


def increment_counter(status: str) -> None:
    if not (counter := counters.get(status)):
        counter = meter.create_counter(
            name=f"run.{status}",
            description=f"number of runs with status {status}",
            unit="1",
        )

        counters[status] = counter

    staging_labels = {"environment": "development"}
    counter.add(1, staging_labels)
