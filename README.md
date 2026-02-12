# loki-mcp

AI-friendly MCP server for [Grafana Loki](https://grafana.com/oss/loki/). Provides 42 tools covering 100% of Loki's HTTP API, plus high-level tools that let LLMs search logs without knowing LogQL.

## Why?

The existing `mcp-loki` gives you 3 raw tools (`loki_query`, `loki_label_names`, `loki_label_values`) and expects the LLM to write LogQL. This project:

- **42 tools** — one per API operation, with typed parameters and rich docstrings
- **No LogQL needed** — high-level tools like `loki_search_logs` build queries from structured params
- **Confirm gates** — mutations (push, delete, flush, shutdown) require `confirm=True`
- **Module filtering** — enable only the modules you need
- **Read-only mode** — strip all write operations
- **100% tested** — 20 unit tests + 36 integration tests against a live Loki instance

## Quick Start

### Nix (recommended)

```bash
nix run github:abl030/loki-mcp
```

### MCP client configuration

Add to your MCP client config (e.g. `.mcp.json`):

```json
{
  "mcpServers": {
    "loki": {
      "command": "nix",
      "args": ["run", "github:abl030/loki-mcp"],
      "env": {
        "LOKI_URL": "https://loki.example.com:3100"
      }
    }
  }
}
```

### uv (no Nix)

```bash
git clone https://github.com/abl030/loki-mcp.git
cd loki-mcp
uv run fastmcp run generated/server.py
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOKI_URL` | `http://localhost:3100` | Loki base URL |
| `LOKI_USERNAME` | *(none)* | Basic auth username |
| `LOKI_PASSWORD` | *(none)* | Basic auth password |
| `LOKI_TOKEN` | *(none)* | Bearer token (alternative to basic auth) |
| `LOKI_ORG_ID` | *(none)* | Multi-tenant org ID (`X-Scope-OrgID` header) |
| `LOKI_VERIFY_SSL` | `false` | Verify SSL certificates |
| `LOKI_MODULES` | *(all)* | Comma-separated modules to enable |
| `LOKI_READ_ONLY` | `false` | Strip all mutation tools |
| `LOKI_TIMEOUT` | `30` | HTTP request timeout in seconds |

### Module Filtering

Restrict which tool groups are available by setting `LOKI_MODULES`:

```bash
# Only expose query and status tools
LOKI_MODULES=query,status
```

### Read-Only Mode

Strip all write operations (push, delete, rules CRUD, admin mutations):

```bash
LOKI_READ_ONLY=true
```

## Tool Inventory

### High-Level Tools (no LogQL needed)

These are the tools most LLMs should use — they build LogQL internally:

| Tool | Description |
|------|-------------|
| `loki_search_logs` | Search by host, container, unit, pattern, severity |
| `loki_error_summary` | Aggregate errors across containers for a host |
| `loki_volume_by_label` | Find noisiest hosts/containers by log volume |
| `loki_compare_hosts` | Side-by-side log comparison across hosts |
| `loki_get_overview` | System summary (health, version, labels, hosts) |
| `loki_validate_query` | Check if a LogQL query is valid |
| `loki_search_tools` | Keyword search across all tool names/descriptions |
| `loki_report_issue` | Generate structured bug report |

### Query Module (6 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_query_instant` | GET | `/loki/api/v1/query` |
| `loki_query_range` | GET | `/loki/api/v1/query_range` |
| `loki_list_labels` | GET | `/loki/api/v1/labels` |
| `loki_list_label_values` | GET | `/loki/api/v1/label/{name}/values` |
| `loki_list_series` | GET | `/loki/api/v1/series` |
| `loki_format_query` | GET | `/loki/api/v1/format_query` |

### Index Module (3 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_index_stats` | GET | `/loki/api/v1/index/stats` |
| `loki_index_volume` | GET | `/loki/api/v1/index/volume` |
| `loki_index_volume_range` | GET | `/loki/api/v1/index/volume_range` |

### Patterns Module (1 tool)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_detect_patterns` | GET | `/loki/api/v1/patterns` |

### Ingest Module (1 tool)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_push` | POST | `/loki/api/v1/push` |

### Rules Module (7 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_list_rules` | GET | `/loki/api/v1/rules` |
| `loki_get_rules_namespace` | GET | `/loki/api/v1/rules/{namespace}` |
| `loki_get_rule_group` | GET | `/loki/api/v1/rules/{namespace}/{group}` |
| `loki_create_rule_group` | POST | `/loki/api/v1/rules/{namespace}` |
| `loki_delete_rule_group` | DELETE | `/loki/api/v1/rules/{namespace}/{group}` |
| `loki_delete_rules_namespace` | DELETE | `/loki/api/v1/rules/{namespace}` |
| `loki_list_prometheus_rules` | GET | `/prometheus/api/v1/rules` |

### Delete Module (3 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_create_delete_request` | POST | `/loki/api/v1/delete` |
| `loki_list_delete_requests` | GET | `/loki/api/v1/delete` |
| `loki_cancel_delete_request` | DELETE | `/loki/api/v1/delete` |

### Status Module (7 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_ready` | GET | `/ready` |
| `loki_metrics` | GET | `/metrics` |
| `loki_config` | GET | `/config` |
| `loki_services` | GET | `/services` |
| `loki_buildinfo` | GET | `/loki/api/v1/status/buildinfo` |
| `loki_get_log_level` | GET | `/log_level` |
| `loki_set_log_level` | POST | `/log_level` |

### Admin Module (6 tools)

| Tool | Method | Endpoint |
|------|--------|----------|
| `loki_flush` | POST | `/flush` |
| `loki_prepare_shutdown_status` | GET | `/ingester/prepare_shutdown` |
| `loki_prepare_shutdown` | POST | `/ingester/prepare_shutdown` |
| `loki_cancel_prepare_shutdown` | DELETE | `/ingester/prepare_shutdown` |
| `loki_shutdown_status` | GET | `/ingester/shutdown` |
| `loki_shutdown` | POST | `/ingester/shutdown` |

## Architecture

```
spec/endpoint-inventory.json  -->  generator/  -->  templates/server.py.j2  -->  generated/server.py
```

The server is **code-generated** from a hand-crafted endpoint spec (Loki has no OpenAPI). To update:

```bash
# Edit spec/endpoint-inventory.json
# Then regenerate:
nix develop -c python -m generator
```

## Testing

### Unit Tests (no infrastructure needed)

```bash
nix develop -c python -m pytest tests/test_naming.py tests/test_modules.py tests/test_list_tools.py -v
```

### Integration Tests (needs Docker)

```bash
# Start Loki test stack
docker compose -f docker/docker-compose.yml up -d

# Wait for ready + seed test data
bash docker/wait-for-ready.sh

# Run 36 integration tests
nix develop -c python -m pytest tests/test_integration.py -v --integration

# Tear down
docker compose -f docker/docker-compose.yml down
```

The Docker stack includes:
- **Loki 3.4.2** (single-binary, all features enabled)
- **Alloy** (log collector scraping flog containers)
- **flog** (4 containers generating realistic logs across 2 simulated hosts)
- **Grafana** (optional, `--profile debug`)

## Known Limitations

- **WebSocket tail** (`/loki/api/v1/tail`) — not supported by FastMCP's transport
- **OTLP ingest** (`/otlp/v1/logs`) — collector protocol, not useful for AI agents
- **Rules CRUD** — requires Loki ruler with remote storage (local storage is read-only for API writes)
- **GET `/ingester/shutdown`** — may trigger actual shutdown in Loki 3.4.x (use with caution)

## License

MIT
