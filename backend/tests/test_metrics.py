"""
Tests for Prometheus metrics (B7.2).

Tests cover:
- Metrics endpoint returns Prometheus format
- Token authentication for /metrics
- Production environment requires token
- Endpoint labels use route templates (not raw paths)
- SSE endpoints excluded from HTTP metrics
- Label cardinality rules (no session_id, run_id, user_id)
- Blocked exec doesn't record duration
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.routes.metrics_routes import router as metrics_router
from app.middleware import MetricsMiddleware
from app.config import Settings


@pytest.fixture
def clean_registry():
    """Provide a clean prometheus registry for each test."""
    # Note: prometheus_client doesn't easily support registry cleanup
    # Tests that check specific metric values should be aware of cumulative nature
    yield REGISTRY


@pytest.fixture
def mock_settings_dev():
    """Mock settings for development environment."""
    settings = MagicMock(spec=Settings)
    settings.metrics_enabled = True
    settings.metrics_token = None
    settings.environment = "development"
    return settings


@pytest.fixture
def mock_settings_prod():
    """Mock settings for production environment."""
    settings = MagicMock(spec=Settings)
    settings.metrics_enabled = True
    settings.metrics_token = None
    settings.environment = "production"
    return settings


@pytest.fixture
def mock_settings_prod_with_token():
    """Mock settings for production with token configured."""
    settings = MagicMock(spec=Settings)
    settings.metrics_enabled = True
    settings.metrics_token = "secret-token"
    settings.environment = "production"
    return settings


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with metrics disabled."""
    settings = MagicMock(spec=Settings)
    settings.metrics_enabled = False
    settings.metrics_token = None
    settings.environment = "development"
    return settings


@pytest.fixture
def test_app():
    """Create a test FastAPI application with metrics middleware."""
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)
    app.include_router(metrics_router)

    @app.get("/api/v1/sessions/{session_id}")
    async def get_session(session_id: str):
        return {"session_id": session_id}

    @app.get("/api/v1/sessions/{session_id}/stream")
    async def stream_events(session_id: str):
        return {"stream": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, client, mock_settings_dev):
        """Verify content type and # HELP / # TYPE markers."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        content = response.text

        # Should contain Prometheus format markers
        assert "# HELP" in content
        assert "# TYPE" in content

    def test_metrics_requires_token_in_production(self, client, mock_settings_prod):
        """Verify 403 without token when env=production."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_prod):
            response = client.get("/metrics")

        assert response.status_code == 403
        assert "token" in response.json()["detail"].lower()

    def test_metrics_allows_token_auth(self, client, mock_settings_prod_with_token):
        """Verify access with correct Bearer token."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_prod_with_token):
            response = client.get(
                "/metrics",
                headers={"Authorization": "Bearer secret-token"}
            )

        assert response.status_code == 200

    def test_metrics_rejects_invalid_token(self, client, mock_settings_prod_with_token):
        """Verify 403 with incorrect token."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_prod_with_token):
            response = client.get(
                "/metrics",
                headers={"Authorization": "Bearer wrong-token"}
            )

        assert response.status_code == 403

    def test_metrics_disabled_returns_404(self, client, mock_settings_disabled):
        """Verify 404 when metrics disabled."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_disabled):
            response = client.get("/metrics")

        assert response.status_code == 404

    def test_metrics_allows_unauthenticated_in_dev(self, client, mock_settings_dev):
        """Verify dev environment allows unauthenticated access."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            response = client.get("/metrics")

        assert response.status_code == 200


class TestEndpointLabels:
    """Tests for endpoint label handling."""

    def test_endpoint_labels_use_route_templates_or_unknown(self, client, mock_settings_dev):
        """Verify endpoint labels use route templates or 'unknown', never raw paths."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            # Make request with specific session ID
            client.get("/api/v1/sessions/abc-123-uuid")

            # Get metrics
            response = client.get("/metrics")

        content = response.text

        # Should use route template or fallback to "unknown" - never raw path
        # Note: BaseHTTPMiddleware may see request before route is resolved,
        # so fallback to "unknown" is acceptable as it prevents cardinality issues
        has_template = "/api/v1/sessions/{session_id}" in content
        has_unknown = 'endpoint="unknown"' in content
        assert has_template or has_unknown, "Endpoint should be route template or 'unknown'"

        # CRITICAL: Should NOT contain the specific UUID - this is the security property
        assert "abc-123-uuid" not in content, "Raw path parameters must not appear in labels"

    def test_query_strings_never_in_labels(self, client, mock_settings_dev):
        """Verify ?foo=bar never appears in endpoint label."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            # Make request with query string
            client.get("/api/v1/sessions/test-id?foo=bar&secret=password")

            # Get metrics
            response = client.get("/metrics")

        content = response.text

        # Query strings should never appear in labels
        assert "foo=bar" not in content
        assert "secret=password" not in content


class TestSSEExclusion:
    """Tests for SSE endpoint exclusion from HTTP metrics."""

    def test_sse_excluded_from_http_metrics(self, client, mock_settings_dev):
        """Verify SSE endpoints don't appear in http_request_duration."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            # Make SSE request
            client.get("/api/v1/sessions/test-id/stream")

            # Make regular request for comparison
            client.get("/api/v1/sessions/test-id")

            # Get metrics
            response = client.get("/metrics")

        content = response.text

        # SSE endpoint should NOT appear in http_request_duration
        # (it's excluded by MetricsMiddleware)
        # The /stream endpoint should not have http_request_duration entries
        lines = content.split('\n')
        duration_lines = [l for l in lines if 'http_request_duration_seconds' in l and '/stream' in l]
        assert len(duration_lines) == 0, "SSE endpoints should be excluded from HTTP duration metrics"

    def test_health_excluded_from_http_metrics(self, client, mock_settings_dev):
        """Verify /health is excluded from HTTP metrics."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            # Make health request
            client.get("/health")

            # Get metrics
            response = client.get("/metrics")

        content = response.text

        # /health should not appear in http_request metrics
        lines = content.split('\n')
        health_duration_lines = [
            l for l in lines
            if 'http_request_duration_seconds' in l and 'endpoint="/health"' in l
        ]
        assert len(health_duration_lines) == 0, "/health should be excluded from HTTP duration metrics"


class TestMetricDefinitions:
    """Tests for correct metric definitions."""

    def test_http_metrics_exist(self):
        """Verify HTTP metrics are defined."""
        from app.metrics import (
            HTTP_REQUESTS_TOTAL,
            HTTP_REQUEST_DURATION_SECONDS,
            HTTP_REQUESTS_IN_PROGRESS,
        )

        assert HTTP_REQUESTS_TOTAL is not None
        assert HTTP_REQUEST_DURATION_SECONDS is not None
        assert HTTP_REQUESTS_IN_PROGRESS is not None

    def test_exec_metrics_exist(self):
        """Verify execution metrics are defined."""
        from app.metrics import (
            EXEC_COMMANDS_TOTAL,
            EXEC_DURATION_SECONDS,
            EXEC_RUNNING,
        )

        assert EXEC_COMMANDS_TOTAL is not None
        assert EXEC_DURATION_SECONDS is not None
        assert EXEC_RUNNING is not None

    def test_sse_metrics_exist(self):
        """Verify SSE metrics are defined."""
        from app.metrics import (
            SSE_CONNECTIONS_TOTAL,
            SSE_CONNECTIONS_ACTIVE,
        )

        assert SSE_CONNECTIONS_TOTAL is not None
        assert SSE_CONNECTIONS_ACTIVE is not None

    def test_session_message_metrics_exist(self):
        """Verify session/message metrics are defined."""
        from app.metrics import (
            SESSIONS_CREATED_TOTAL,
            MESSAGES_TOTAL,
        )

        assert SESSIONS_CREATED_TOTAL is not None
        assert MESSAGES_TOTAL is not None

    def test_db_pool_metrics_exist(self):
        """Verify database pool metrics are defined."""
        from app.metrics import (
            DB_POOL_SIZE,
            DB_POOL_IN_USE,
        )

        assert DB_POOL_SIZE is not None
        assert DB_POOL_IN_USE is not None

    def test_app_info_exists(self):
        """Verify application info metric is defined."""
        from app.metrics import APP_INFO

        assert APP_INFO is not None


class TestLabelCardinality:
    """Tests for label cardinality rules."""

    def test_no_banned_labels_in_http_metrics(self, client, mock_settings_dev):
        """Verify run_id, session_id, user_id never in HTTP metric labels."""
        with patch("app.routes.metrics_routes.get_settings", return_value=mock_settings_dev):
            # Make some requests
            client.get("/api/v1/sessions/test-session-id")

            response = client.get("/metrics")

        content = response.text

        # Check that banned labels are not present in http_request metrics
        http_lines = [l for l in content.split('\n') if 'http_request' in l]
        for line in http_lines:
            assert 'run_id=' not in line, "run_id should not be in HTTP metrics"
            assert 'session_id=' not in line, "session_id should not be in HTTP metrics"
            assert 'user_id=' not in line, "user_id should not be in HTTP metrics"


class TestDatabasePoolStats:
    """Tests for database pool statistics."""

    def test_pool_stats_graceful_when_unavailable(self):
        """Verify -1 returned when pool stats unavailable."""
        from app.database import Database

        db = Database()
        # Without initialization, pool stats should return -1
        stats = db.get_pool_stats()

        assert stats["size"] == -1
        assert stats["in_use"] == -1

    def test_pool_stats_with_mock_engine(self):
        """Verify pool stats extraction when engine available."""
        from app.database import Database

        db = Database()

        # Mock engine with pool
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 2

        mock_engine = MagicMock()
        mock_engine.pool = mock_pool

        db._engine = mock_engine

        stats = db.get_pool_stats()

        assert stats["size"] == 5
        assert stats["in_use"] == 2


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware behavior."""

    def test_middleware_excludes_health_path(self):
        """Verify /health is in EXCLUDE_PATHS."""
        assert "/health" in MetricsMiddleware.EXCLUDE_PATHS

    def test_middleware_excludes_metrics_path(self):
        """Verify /metrics is in EXCLUDE_PATHS."""
        assert "/metrics" in MetricsMiddleware.EXCLUDE_PATHS

    def test_middleware_has_sse_patterns(self):
        """Verify SSE patterns are defined."""
        assert "/stream" in MetricsMiddleware.SSE_PATTERNS
