# Loki MCP Server

## Goal

Build an AI-friendly MCP server for Grafana Loki. Unlike the existing 3-tool `mcp-loki` wrapper, this server provides 42 tools covering 100% of Loki's HTTP API plus high-level tools that let LLMs search logs without knowing LogQL.

**Repo:** `abl030/loki-mcp` — https://github.com/abl030/loki-mcp

## Architecture

### Generator Pattern

Same pattern as `unifi-mcp-generator`: hand-crafted endpoint spec -> generator -> Jinja2 template -> generated server.

```
spec/endpoint-inventory.json  -->  generator/  -->  templates/server.py.j2  -->  generated/server.py
```

### Directory Structure

```
~/loki-mcp/
├── CLAUDE.md                    # This file — project rules + plan
├── README.md                    # User-facing docs
├── flake.nix                    # Nix packaging (writeShellApplication + fastmcp run)
├── flake.lock
├── pyproject.toml               # uv project config (fastmcp, httpx, jinja2, pytest)
├── spec/
│   └── endpoint-inventory.json  # Hand-crafted Loki API spec (34 endpoints, 9 modules)
├── generator/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m generator [--dry-run]
│   ├── loader.py                # Load + parse endpoint-inventory.json
│   ├── context_builder.py       # Build Jinja2 template context from spec
│   ├── codegen.py               # Render template + write generated/server.py
│   └── naming.py                # Module constants, type mappings
├── templates/
│   └── server.py.j2             # Jinja2 server template (~600 lines)
├── generated/
│   └── server.py                # Generated MCP server (1756 lines, 42 tools) — DO NOT EDIT
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # --integration flag, loki_url fixture
│   ├── test_naming.py           # 4 unit tests: naming conventions
│   ├── test_modules.py          # 8 unit tests: spec parsing, module assignment
│   ├── test_list_tools.py       # 8 unit tests: tool registration, confirm gates
│   └── test_integration.py      # 36 integration tests: all modules against live Loki
├── bank-tester/                 # (Scaffolded, not yet populated)
│   ├── tasks/
│   └── results/
└── docker/
    ├── docker-compose.yml       # Loki 3.4.2 + Alloy + 4x flog + optional Grafana
    ├── loki-config.yaml         # Full-featured Loki config
    ├── alloy-config.alloy       # Alloy scrape config for flog containers
    ├── seed-data.py             # Deterministic test data seeder
    └── wait-for-ready.sh        # Poll /ready + run seed-data.py
```

### Key Files

- `spec/endpoint-inventory.json` — Single source of truth for all Loki endpoints. Each entry has: id, module, method, path, tool_name, description, mutation, danger, parameters, response_fields, notes. Also defines 8 high_level_tools and 9 module definitions.
- `templates/server.py.j2` — Generates the full FastMCP server including: config from env vars, module gating, timestamp helper, LokiClient (httpx async), response formatting, all direct API tools, all high-level tools, tool discovery dict.
- `generated/server.py` — NEVER edit directly. Regenerate with `python -m generator`.

### Modules (9)

| Module | Description | Tools |
|--------|-------------|-------|
| query | Log/metric queries, labels, series | 5 |
| index | Index stats, volume analysis | 3 |
| patterns | Pattern detection | 1 |
| ingest | Push log entries | 1 |
| rules | Alert rule CRUD | 7 |
| delete | Log deletion management | 3 |
| status | Health, metrics, config, services | 7 |
| admin | Flush, shutdown management | 6 |
| format | Query formatting/validation | 1 |

Plus 8 high-level tools (search_logs, error_summary, volume_by_label, compare_hosts, get_overview, search_tools, report_issue, validate_query). **Total: 42 tools.**

## Critical Rules

1. **NEVER manually edit `generated/server.py`** — all fixes go through the generator or template
2. **All mutations require `confirm=True`** — push, delete, flush, shutdown, rules CRUD
3. **All tools prefixed with `loki_`** — consistent naming
4. **Module gating via `LOKI_MODULES` env var** — comma-separated list
5. **Read-only mode via `LOKI_READ_ONLY` env var** — strips mutation tools
6. **Dangerous ops get warning** — delete, flush, shutdown show DANGEROUS OPERATION message

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOKI_URL` | `http://localhost:3100` | Loki base URL |
| `LOKI_USERNAME` | *(none)* | Basic auth username |
| `LOKI_PASSWORD` | *(none)* | Basic auth password |
| `LOKI_TOKEN` | *(none)* | Bearer token |
| `LOKI_ORG_ID` | *(none)* | Multi-tenant org ID (`X-Scope-OrgID` header) |
| `LOKI_VERIFY_SSL` | `false` | Verify SSL certificates |
| `LOKI_MODULES` | *(all)* | Comma-separated modules to enable |
| `LOKI_READ_ONLY` | `false` | Strip mutation tools |
| `LOKI_TIMEOUT` | `30` | Request timeout in seconds |

## Running

```bash
# Run server via Nix
nix run .

# Development shell
nix develop

# Regenerate server.py from spec + template
python -m generator
python -m generator --dry-run   # Preview only

# Unit tests (no infra needed)
python -m pytest tests/test_naming.py tests/test_modules.py tests/test_list_tools.py -v

# Integration tests (needs Docker + seeded Loki)
docker compose -f docker/docker-compose.yml up -d
bash docker/wait-for-ready.sh
python -m pytest tests/test_integration.py -v --integration
docker compose -f docker/docker-compose.yml down
```

## Testing

### Test Suite Summary

- **20 unit tests**: naming conventions, spec parsing, module assignment, tool registration, confirm gates, danger warnings, module gating, readonly gating, tool discovery dict
- **36 integration tests**: all 9 modules tested against live Loki in Docker. Covers status (8), query (6), index (3), ingest (2), delete (2), admin (3), high-level (10), module gating (2)

### Integration Test Patterns

- FastMCP's `@mcp.tool()` wraps functions in `FunctionTool` objects. Tests extract `.fn` via `getattr(tool, "fn", tool)` to call the underlying async function directly.
- Each `_call()` creates a fresh `LokiClient()` because `asyncio.run()` creates/closes event loops, and httpx AsyncClient connections don't survive across event loops.
- `test_push_and_query` runs push + query in a single `async def` with one `asyncio.run()` to share the event loop.
- `GET /ingester/shutdown` is NOT tested — it can trigger actual shutdown in Loki 3.4.x.

### Docker Test Stack

- **Loki 3.4.2** — single-binary, all features enabled (volume, patterns, ruler, compactor with deletion)
- **Alloy v1.5.1** — scrapes flog containers, adds host/container labels
- **flog 0.4.3** — 4 containers: host1-nginx (apache), host1-app (json), host2-nginx (apache), host2-db (rfc5424)
- **seed-data.py** — pushes deterministic data: basic logs (2 hosts x 3 containers x 20 lines), error logs (6 patterns), JSON logs (10 entries)
- **Grafana** (optional, `--profile debug`) — visual debugging on port 3000

## Known Limitations

- **WebSocket tail** (`/loki/api/v1/tail`) — not supported by FastMCP's transport
- **OTLP ingest** (`/otlp/v1/logs`) — collector protocol, not useful for AI agents
- **Rules CRUD via API** — requires ruler with remote storage (local storage returns `SetRuleGroup unsupported`)
- **GET `/ingester/shutdown`** — may trigger actual shutdown in Loki 3.4.x, not just return status

## Key Design Decisions

1. **Hand-crafted spec, not OpenAPI**: Loki has no OpenAPI spec. `endpoint-inventory.json` is written by hand from official docs. This is the single source of truth.
2. **Generator pattern preserved**: Even though the API is small (34 endpoints), the generator keeps updates systematic. When Loki adds endpoints, update the spec and re-run.
3. **High-level tools are the differentiator**: Direct API tools give 100% coverage. High-level tools (`search_logs`, `error_summary`, etc.) eliminate the need for LLMs to know LogQL.
4. **Confirm gate on mutations**: Same pattern as pfsense-mcp/unifi-mcp. All write operations require `confirm=True`.
5. **Docker over VM**: Loki runs natively in Docker (unlike pfSense which needs QEMU). Fast test cycles.
6. **Timestamp helper**: All timestamp params accept human-friendly "1h", "30m", "2d" and convert to RFC3339 internally.

---

## Sprint Plan — Status

### Sprint 0: Project Scaffolding — DONE
- [x] Directory structure, pyproject.toml, flake.nix, .gitignore, CLAUDE.md
- [x] Minimal generated/server.py stub
- [x] git init + initial commit
- [x] `nix run` starts server, `nix develop` enters shell
- [x] GitHub repo created: `abl030/loki-mcp`

### Sprint 1: Endpoint Spec + Generator Foundation — DONE
- [x] `spec/endpoint-inventory.json` — 34 endpoints, 9 modules, 8 high-level tools
- [x] `generator/loader.py` — dataclasses + JSON parsing
- [x] `generator/naming.py` — module constants, type mappings
- [x] `generator/context_builder.py` — template context builder
- [x] `generator/__main__.py` — CLI with --dry-run
- [x] `tests/test_naming.py` — 4 tests
- [x] `python -m generator --dry-run` lists all 42 tools

### Sprint 2: Template + Code Generation — DONE
- [x] `templates/server.py.j2` — full Jinja2 template (~600 lines)
- [x] `generator/codegen.py` — render + write
- [x] Timestamp normalization, multi-tenant support, LogQL pass-through
- [x] `tests/test_modules.py` — 8 tests
- [x] `tests/test_list_tools.py` — 8 tests
- [x] Generated server.py compiles, 42 tools registered, 20 unit tests pass

### Sprint 3: High-Level AI-Friendly Tools — DONE
- [x] loki_search_logs, loki_error_summary, loki_volume_by_label
- [x] loki_compare_hosts, loki_get_overview
- [x] loki_search_tools, loki_report_issue, loki_validate_query
- [x] All included in template, generated into server.py

### Sprint 4: Docker Test Infrastructure — DONE
- [x] docker-compose.yml — Loki + Alloy + 4x flog + optional Grafana
- [x] loki-config.yaml — all features enabled
- [x] alloy-config.alloy — scrape + label flog containers
- [x] seed-data.py — deterministic test data
- [x] wait-for-ready.sh — readiness polling + seed
- [x] Note: Ruler API writes not supported with local storage (read-only limitation)

### Sprint 5: HTTP Integration Tests — DONE
- [x] conftest.py with --integration flag
- [x] test_integration.py — 36 tests across all modules
- [x] All 56 tests pass (20 unit + 36 integration)
- [x] Fixes: FunctionTool .fn extraction, fresh httpx client per call, event loop isolation

### Sprint 6: LLM Bank Testing — SKIPPED
- [ ] bank-tester/ infrastructure (TESTER-CLAUDE.md, task-config, runner, analyzer)
- Deferred — manual testing sufficient for current scope

### Sprint 7: Polish + Release — PARTIALLY DONE
- [x] README.md with install, config, tool inventory, testing docs
- [x] CLAUDE.md updated with full project state
- [x] Pushed to GitHub
- [ ] Wire into nixosconfig (.mcp.json, claude-code.nix)
- [ ] Tag v1.0.0

## Verification Commands

```bash
# Regenerate server from spec
nix develop -c python -m generator

# Run all unit tests
nix develop -c python -m pytest tests/test_naming.py tests/test_modules.py tests/test_list_tools.py -v

# Run integration tests (Docker must be running with seeded data)
nix develop -c python -m pytest tests/test_integration.py -v --integration

# Start server on stdio
nix run .
```
