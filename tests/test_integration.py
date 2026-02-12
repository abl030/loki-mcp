"""Integration tests against a live Loki instance.

Run with: python -m pytest tests/test_integration.py -v --integration
Requires Loki at LOKI_TEST_URL (default: http://localhost:3100) with seeded data.
"""

import asyncio
import json
import os
import sys
import time

import pytest

# Ensure we can import the generated server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def set_loki_env(loki_url, monkeypatch):
    """Set LOKI_URL for the generated server module."""
    monkeypatch.setenv("LOKI_URL", loki_url)
    monkeypatch.setenv("LOKI_VERIFY_SSL", "false")


def _load_server():
    """Import the generated server (fresh for each test).

    FastMCP's @mcp.tool() wraps async functions in FunctionTool objects.
    We extract the underlying .fn for direct invocation in tests.
    """
    # Force reload to pick up env changes
    if "generated.server" in sys.modules:
        del sys.modules["generated.server"]
    import generated.server as srv
    # Re-init the client with the correct URL
    srv._client = srv.LokiClient()
    return srv


def _call(tool_attr, **kwargs):
    """Call a FastMCP tool function, extracting .fn from FunctionTool wrapper.

    Creates a fresh httpx client each time to avoid event loop issues
    since asyncio.run() creates and closes event loops.
    """
    fn = getattr(tool_attr, "fn", tool_attr)
    # Get the module and ensure a fresh client for this event loop
    import generated.server as srv
    srv._client = srv.LokiClient()
    return asyncio.run(fn(**kwargs))


# ===========================================================================
# Status module
# ===========================================================================


class TestStatus:
    def test_ready(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_ready)
        assert "ready" in result.lower()

    def test_buildinfo(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_buildinfo)
        data = json.loads(result)
        assert "version" in data

    def test_config(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_config)
        assert len(result) > 0

    def test_services(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_services)
        assert len(result) > 0

    def test_metrics(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_metrics)
        assert "loki" in result.lower() or "go_" in result

    def test_get_log_level(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_get_log_level)
        assert result  # non-empty

    def test_set_log_level_dry_run(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_set_log_level, log_level="debug", confirm=False)
        assert "DRY RUN" in result

    def test_set_log_level(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_set_log_level, log_level="info", confirm=True)
        assert result  # non-empty


# ===========================================================================
# Query module
# ===========================================================================


class TestQuery:
    def test_list_labels(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_list_labels)
        data = json.loads(result)
        assert isinstance(data, list)
        assert "host" in data

    def test_list_label_values(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_list_label_values, name="host")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_query_instant(self, loki_url):
        """Instant query with a metric-style aggregation."""
        srv = _load_server()
        # Instant queries with log selectors need time param;
        # use count_over_time which returns a vector
        result = _call(srv.loki_query_instant,
            query='count_over_time({host=~".+"}[5m])', limit=5
        )
        assert "result" in result

    def test_query_range(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_query_range,
            query='{host=~".+"}', start="1h", limit=10
        )
        assert "result" in result

    def test_list_series(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_list_series, match='{host=~".+"}')
        data = json.loads(result)
        assert isinstance(data, list)

    def test_format_query(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_format_query, query='{host="test-host-1"}')
        assert result  # non-empty


# ===========================================================================
# Index module
# ===========================================================================


class TestIndex:
    def test_index_stats(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_index_stats, query='{host=~".+"}')
        data = json.loads(result)
        assert "streams" in data or "bytes" in data

    def test_index_volume(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_index_volume,
            query='{host=~".+"}', targetLabels="host"
        )
        assert result  # non-empty

    def test_index_volume_range(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_index_volume_range,
            query='{host=~".+"}', start="1h", step="15m"
        )
        assert result  # non-empty


# ===========================================================================
# Ingest module
# ===========================================================================


class TestIngest:
    def test_push_dry_run(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_push,
            streams=[{"stream": {"test": "true"}, "values": []}],
            confirm=False,
        )
        assert "DRY RUN" in result

    def test_push_and_query(self, loki_url):
        """Push a log entry, then query it back in the same event loop."""
        srv = _load_server()
        ts = str(int(time.time() * 1e9))
        marker = f"integration-test-{int(time.time())}"

        # Run push + query in a single asyncio.run() to share the event loop
        async def _push_and_verify():
            import generated.server as mod
            mod._client = mod.LokiClient()
            push_fn = getattr(mod.loki_push, "fn", mod.loki_push)
            query_fn = getattr(mod.loki_query_range, "fn", mod.loki_query_range)

            result = await push_fn(
                streams=[{
                    "stream": {"host": "test-integration", "container": "pytest"},
                    "values": [[ts, f"Integration test marker: {marker}"]],
                }],
                confirm=True,
            )
            assert "success" in result.lower()

            # Wait for ingestion
            await asyncio.sleep(2)

            # Query it back
            result = await query_fn(
                query='{host="test-integration"}', start="5m", limit=10
            )
            return result

        result = asyncio.run(_push_and_verify())
        assert marker in result


# ===========================================================================
# Delete module
# ===========================================================================


class TestDelete:
    def test_list_delete_requests(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_list_delete_requests)
        # May return empty list or list of requests
        assert result  # non-empty

    def test_create_delete_request_dry_run(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_create_delete_request,
            query='{host="nonexistent"}',
            start="2024-01-01T00:00:00Z",
            end="2024-01-02T00:00:00Z",
            confirm=False,
        )
        assert "DANGEROUS OPERATION" in result


# ===========================================================================
# Admin module
# ===========================================================================


class TestAdmin:
    def test_flush_dry_run(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_flush, confirm=False)
        assert "DANGEROUS OPERATION" in result

    def test_prepare_shutdown_status(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_prepare_shutdown_status)
        assert result  # non-empty

    def test_shutdown_dry_run(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_shutdown, confirm=False)
        assert "DANGEROUS OPERATION" in result

    # NOTE: test_shutdown_status skipped — GET /ingester/shutdown can trigger
    # actual shutdown in Loki 3.4.x, crashing the test instance.


# ===========================================================================
# High-level tools
# ===========================================================================


class TestHighLevel:
    def test_search_logs(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_search_logs,
            host="test-host-1", start="1h", limit=10
        )
        assert "Query:" in result

    def test_search_logs_with_pattern(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_search_logs,
            host="test-host-1", pattern="error", start="1h", limit=10
        )
        assert "Query:" in result

    def test_error_summary(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_error_summary,
            host="test-host-1", start="1h"
        )
        assert "error_summary" in result.lower() or "Error summary" in result

    def test_volume_by_label(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_volume_by_label,
            label="host", start="1h"
        )
        assert "Volume by host" in result

    def test_compare_hosts(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_compare_hosts,
            hosts="test-host-1,test-host-2", start="1h"
        )
        assert "Comparing" in result

    def test_get_overview(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_get_overview)
        assert "Loki System Overview" in result
        data = json.loads(result.split("\n\n", 1)[1])
        assert data["ready"] is True
        assert "labels" in data

    def test_search_tools(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_search_tools, keyword="query")
        parsed = json.loads(result.split("\n\n", 1)[1])
        assert len(parsed["matches"]) > 0

    def test_report_issue(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_report_issue,
            tool_name="loki_ready",
            error="Test error",
        )
        assert "gh issue create" in result

    def test_validate_query_valid(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_validate_query, query='{host="test"}')
        assert "valid" in result.lower()

    def test_validate_query_invalid(self, loki_url):
        srv = _load_server()
        result = _call(srv.loki_validate_query, query="this is not logql")
        # Should handle gracefully
        assert result  # non-empty


# ===========================================================================
# Module gating
# ===========================================================================


class TestModuleGating:
    def test_module_disabled(self, loki_url, monkeypatch):
        monkeypatch.setenv("LOKI_MODULES", "status")
        srv = _load_server()
        result = _call(srv.loki_list_labels)
        assert "not enabled" in result

    def test_readonly_mode(self, loki_url, monkeypatch):
        monkeypatch.setenv("LOKI_READ_ONLY", "true")
        srv = _load_server()
        result = _call(srv.loki_push,
            streams=[{"stream": {}, "values": []}],
            confirm=True,
        )
        assert "read-only" in result
