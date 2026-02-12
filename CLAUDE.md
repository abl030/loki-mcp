# Loki MCP Server

## Goal

Build an AI-friendly MCP server for Grafana Loki. Unlike the existing 3-tool `mcp-loki` wrapper, this server provides ~47 tools covering 100% of Loki's HTTP API plus high-level tools that eliminate the need for LLMs to know LogQL syntax.

## Architecture

### Generator Pattern

Same pattern as `unifi-mcp-generator`: hand-crafted endpoint spec → generator → Jinja2 template → generated server.

```
spec/endpoint-inventory.json  →  generator/  →  templates/server.py.j2  →  generated/server.py
```

### Key Files

- `spec/endpoint-inventory.json` — Hand-crafted Loki API spec (replaces OpenAPI)
- `generator/` — Python package that loads spec + renders template
- `templates/server.py.j2` — Jinja2 template producing the MCP server
- `generated/server.py` — Generated output (DO NOT EDIT)
- `tests/` — Unit tests for generator logic
- `docker/` — Docker Compose stack for integration testing

### Modules (8)

| Module | Description | Tools |
|--------|-------------|-------|
| query | Log/metric queries, labels, series | ~6 |
| index | Index stats, volume analysis | ~3 |
| patterns | Pattern detection | ~1 |
| ingest | Push log entries | ~1 |
| rules | Alert rule CRUD | ~7 |
| delete | Log deletion management | ~3 |
| status | Health, metrics, config, services | ~8 |
| admin | Flush, shutdown management | ~5 |
| format | Query formatting/validation | ~1 |

Plus ~8 high-level AI-friendly tools.

## Critical Rules

1. **NEVER manually edit `generated/server.py`** — all fixes go through the generator
2. **All mutations require `confirm=True`** — push, delete, flush, shutdown, rules CRUD
3. **All tools prefixed with `loki_`** — consistent naming
4. **Module gating via `LOKI_MODULES` env var** — comma-separated list
5. **Read-only mode via `LOKI_READ_ONLY` env var** — strips mutation tools

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOKI_URL` | `http://localhost:3100` | Loki base URL |
| `LOKI_USERNAME` | *(none)* | Basic auth username |
| `LOKI_PASSWORD` | *(none)* | Basic auth password |
| `LOKI_TOKEN` | *(none)* | Bearer token |
| `LOKI_ORG_ID` | *(none)* | Multi-tenant org ID |
| `LOKI_VERIFY_SSL` | `false` | Verify SSL certificates |
| `LOKI_MODULES` | *(all)* | Comma-separated modules to enable |
| `LOKI_READ_ONLY` | `false` | Strip mutation tools |
| `LOKI_TIMEOUT` | `30` | Request timeout in seconds |

## Running

```bash
# Run server via Nix
nix run .

# Development
nix develop
python -m generator          # Regenerate server.py
python -m pytest tests/ -v   # Run unit tests

# Integration tests (needs Docker)
docker compose -f docker/docker-compose.yml up -d
python -m pytest tests/ -v --integration
```

## Tech Stack

- **Python 3.11+**, **FastMCP**, **httpx** (async), **Jinja2**
- **Docker Compose** for test infrastructure (Loki + Alloy + flog)
