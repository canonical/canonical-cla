from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterHTTP,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterGRPC,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import config

tracer_instance: trace.Tracer = None


def register_tracer(app: FastAPI):
    global tracer_instance
    if tracer_instance:
        return tracer_instance
    if not config.otel_exporter.otlp_endpoint:
        print("INFO:app.opentelemetry:", "Tracing is disabled")
        return None

    service_name = "canonical-cla"
    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter: OTLPSpanExporterHTTP | OTLPSpanExporterGRPC = None
    if "4317" in config.otel_exporter.otlp_endpoint:
        otlp_exporter = OTLPSpanExporterGRPC(
            endpoint=config.otel_exporter.otlp_endpoint
        )
        print("INFO:app.opentelemetry:", "Using gRPC exporter")
    else:
        if not "v1/traces" in config.otel_exporter.otlp_endpoint:
            config.otel_exporter.otlp_endpoint = (
                f"{config.otel_exporter.otlp_endpoint}/v1/traces"
            )
        otlp_exporter = OTLPSpanExporterHTTP(
            endpoint=config.otel_exporter.otlp_endpoint
        )
        print("INFO:app.opentelemetry:", "Using HTTP exporter")
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)

    excluded_urls = ["/_status/check", "/metrics"]
    FastAPIInstrumentor.instrument_app(app, excluded_urls=",".join(excluded_urls))

    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    tracer_instance = trace.get_tracer(service_name)
    print("INFO:app.opentelemetry:", "Tracing is enabled")
    return tracer_instance


def tracer() -> trace.Tracer:
    """
    FastAPI service tracer instance.
    """
    return tracer_instance
