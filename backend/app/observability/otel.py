"""OpenTelemetry instrumentation setup for FastAPI application."""

import os
import uuid
from typing import Any

from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.core.config import settings


def _get_sampler() -> Any:
    """Get trace sampler based on environment variables."""
    sampler_type = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
    sampler_arg = os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.1")

    ratio = float(sampler_arg)

    if sampler_type == "traceidratio":
        return TraceIdRatioBased(ratio)
    elif sampler_type == "parentbased_traceidratio":
        # Parent-based: if parent exists, use parent's decision; otherwise use ratio
        return ParentBased(root=TraceIdRatioBased(ratio))
    else:
        # Default: always on (for dev)
        return TraceIdRatioBased(1.0)


def setup_otel() -> None:
    """Configure and initialize OpenTelemetry tracing."""
    # Only setup if OTLP endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return

    # Build resource attributes
    service_name = os.getenv("OTEL_SERVICE_NAME", settings.PROJECT_NAME)
    service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    deployment_env = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")

    # Parse deployment.environment from OTEL_RESOURCE_ATTRIBUTES
    # Format: "deployment.environment=prod,service.name=..."
    env_value = "dev"
    if deployment_env:
        for attr in deployment_env.split(","):
            if "=" in attr:
                key, value = attr.split("=", 1)
                if key.strip() == "deployment.environment":
                    env_value = value.strip()
                    break

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": env_value,
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource, sampler=_get_sampler())
    trace.set_tracer_provider(tracer_provider)

    # Configure OTLP exporter
    # OTLP HTTP exporter automatically appends /v1/traces to the endpoint
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
    )

    # Add batch span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)


def instrument_app(app: FastAPI) -> None:
    """Instrument FastAPI application with OpenTelemetry."""
    # Only instrument if OTLP endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Explicitly instrument SQLAlchemy, Redis, and httpx
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.db.engine import engine
        
        # Instrument SQLAlchemy engine
        SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception:
        # If instrumentation fails, continue without it
        pass

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
    except Exception:
        # If instrumentation fails, continue without it
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception:
        # If instrumentation fails, continue without it
        pass

    # Add middleware to attach request_id to spans
    @app.middleware("http")
    async def add_request_id_to_span(request: Request, call_next: Any) -> Any:
        """Middleware to attach request_id to OpenTelemetry spans."""
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Get current span and add request_id as attribute
        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute("http.request_id", request_id)

            # Only add user_id if available and safe (numeric/UUID, not PII)
            if hasattr(request.state, "user") and request.state.user:
                user_id = getattr(request.state.user, "id", None)
                if user_id:
                    # Only include if it's a UUID or numeric ID (not email/name)
                    try:
                        # Try to convert to UUID or int to ensure it's safe
                        if isinstance(user_id, (int, uuid.UUID)):
                            span.set_attribute("user.id", str(user_id))
                        elif isinstance(user_id, str):
                            # Check if it's a valid UUID format
                            uuid.UUID(user_id)
                            span.set_attribute("user.id", user_id)
                    except (ValueError, AttributeError):
                        # Not a safe ID format, skip it
                        pass

        response = await call_next(request)
        return response
