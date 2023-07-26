from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import \
    CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from infra.logger import log_error

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


def increment_counter(counter_name: str, amount: int = 1) -> None:
    try:
        if not (counter := counters.get(counter_name)):
            counter = meter.create_counter(
                name=counter_name,
            )

            counters[counter_name] = counter

        staging_labels = {"environment": "development"}
        print(f"adding {amount} to {counter_name}")
        counter.add(amount, staging_labels)
    except Exception as e:
        log_error("increment_counter", f"EXCEPTION:{str(e)}")


def run_status(status: str) -> None:
    increment_counter(f"mission.run.{status}", 1)


def mission_amount(amount: float) -> None:
    increment_counter("mission.size", int(amount))
