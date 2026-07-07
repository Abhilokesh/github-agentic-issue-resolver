"""OpenTelemetry span export for agent trajectories (Day 4: trajectory
evaluation / observability). Exports to the console/log by default; set
OTEL_EXPORT_TARGET=gcp (with GOOGLE_CLOUD_PROJECT set and billing active)
to switch to Google Cloud Observability instead.

Import and call configure_tracing() once, before running any workflow.
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

_configured = False


def configure_tracing(service_name: str = "github-issue-agent") -> None:
    global _configured
    if _configured:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))

    if os.environ.get("OTEL_EXPORT_TARGET") == "gcp":
        # Requires: pip install opentelemetry-exporter-gcp-trace, and a GCP
        # project with billing + Cloud Trace API enabled. Kept as an
        # explicit opt-in since this dev environment has neither.
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

        exporter = CloudTraceSpanExporter(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"]
        )
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _configured = True
