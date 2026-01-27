"""Prometheus metrics middleware for FastAPI."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# HTTP request counter: http_requests_total{method, route, status}
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "route", "status"],
)

# HTTP request duration histogram: http_request_duration_seconds{method, route}
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()

        # Get route name (use path if route not available)
        route = request.url.path
        if request.scope.get("route"):
            route_name = getattr(request.scope["route"], "name", None)
            if route_name:
                route = route_name

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        method = request.method
        status_code = str(response.status_code)

        http_requests_total.labels(method=method, route=route, status=status_code).inc()
        http_request_duration_seconds.labels(method=method, route=route).observe(duration)

        return response
