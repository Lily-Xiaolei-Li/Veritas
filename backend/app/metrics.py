"""
Prometheus metrics for Agent B (B7.2).

LABEL RULES (enforced):
- NO run_id, session_id, user_id labels anywhere
- Endpoint labels use FastAPI route templates only
- Fallback to "unknown" if route unavailable
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ============================================================================
# HTTP Request Metrics (excludes SSE endpoints)
# ============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests (excludes SSE streams)",
    labelnames=["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (excludes SSE streams)",
    labelnames=["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Single unlabeled gauge - avoids cardinality issues
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed (excludes SSE)"
)

# ============================================================================
# Executor Metrics
# ============================================================================

EXEC_COMMANDS_TOTAL = Counter(
    "exec_commands_total",
    "Total command execution attempts",
    labelnames=["status"]  # success, failure, timeout, blocked, approval_required
)

# Duration ONLY for actual executions (not blocked/rejected)
EXEC_DURATION_SECONDS = Histogram(
    "exec_duration_seconds",
    "Execution time (actual runtime only)",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

# Running count (not queue depth - there is no queue yet)
EXEC_RUNNING = Gauge(
    "exec_running",
    "Number of executions currently running"
)

# ============================================================================
# SSE Metrics (separate from HTTP)
# ============================================================================

SSE_CONNECTIONS_TOTAL = Counter(
    "sse_connections_total",
    "Total SSE connections opened"
)

SSE_CONNECTIONS_ACTIVE = Gauge(
    "sse_connections_active",
    "Number of active SSE connections"
)

# ============================================================================
# Session/Message Metrics
# ============================================================================

SESSIONS_CREATED_TOTAL = Counter(
    "sessions_created_total",
    "Total sessions created"
)

MESSAGES_TOTAL = Counter(
    "messages_total",
    "Total messages submitted",
    labelnames=["role"]  # user, assistant
)

# ============================================================================
# Database Pool Metrics (best-effort)
# ============================================================================

DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Database connection pool configured size (-1 if unavailable)"
)

DB_POOL_IN_USE = Gauge(
    "db_pool_in_use",
    "Database connections currently in use (-1 if unavailable)"
)

# ============================================================================
# Application Info
# ============================================================================

APP_INFO = Info(
    "agentb",
    "Agent B application information"
)
# Labels: version, environment (NOT hostname, NOT timestamp)
