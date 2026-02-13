"""
Middleware components for Agent B.

Provides request ID tracking, metrics collection, and other cross-cutting concerns.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import clear_request_id, get_logger, set_request_id
from .metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)

logger = get_logger("api.middleware")


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP metrics middleware - excludes SSE endpoints (B7.2).

    Collects:
    - Request count by method, endpoint, status code
    - Request duration by method, endpoint
    - In-progress request count

    Excludes:
    - /health and /metrics endpoints
    - SSE streaming endpoints (/stream)
    """

    # Endpoints excluded from HTTP metrics (SSE, health, metrics itself)
    EXCLUDE_PATHS = {"/health", "/metrics"}
    SSE_PATTERNS = ["/stream"]  # SSE endpoints contain this

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with metrics collection."""
        path = request.url.path

        # Skip excluded paths
        if path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Skip SSE endpoints entirely
        if any(pattern in path for pattern in self.SSE_PATTERNS):
            return await call_next(request)

        # Get endpoint from FastAPI route template (NOT raw path)
        route = request.scope.get("route")
        endpoint = route.path if route else "unknown"
        method = request.method

        HTTP_REQUESTS_IN_PROGRESS.inc()
        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start_time
            HTTP_REQUESTS_IN_PROGRESS.dec()

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates and propagates request IDs.

    Request IDs are:
    - Generated as UUIDs for each request
    - Set in the logging context for automatic inclusion in logs
    - Returned in the X-Request-ID response header
    - Accepted from X-Request-ID request header if provided
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with request ID tracking."""
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set request ID in logging context
        set_request_id(request_id)

        try:
            # Log request
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query) if request.url.query else None,
                        "client": request.client.host if request.client else None,
                    }
                }
            )

            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response
            logger.info(
                f"Response {response.status_code}",
                extra={
                    "extra_fields": {
                        "status_code": response.status_code,
                    }
                }
            )

            return response

        except Exception as e:
            logger.error(
                f"Request failed: {e}",
                exc_info=True,
                extra={"extra_fields": {"error": str(e)}}
            )
            raise

        finally:
            # Clear request ID from context
            clear_request_id()
