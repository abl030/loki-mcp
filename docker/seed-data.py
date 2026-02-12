#!/usr/bin/env python3
"""Seed Loki with structured test data for deterministic testing."""

import json
import time
import sys

import httpx

LOKI_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"


def ns_timestamp(seconds_ago: int = 0) -> str:
    """Generate nanosecond Unix timestamp."""
    return str(int((time.time() - seconds_ago) * 1e9))


def push(streams: list[dict]) -> None:
    """Push log entries to Loki."""
    resp = httpx.post(f"{LOKI_URL}/loki/api/v1/push", json={"streams": streams})
    if resp.status_code not in (200, 204):
        print(f"  WARN: push returned {resp.status_code}: {resp.text[:200]}")
    else:
        print(f"  Pushed {len(streams)} stream(s)")


def seed_basic_logs():
    """Push basic log lines for various hosts/containers."""
    print("Seeding basic logs...")
    hosts = ["test-host-1", "test-host-2"]
    containers = ["nginx", "app", "db"]

    for host in hosts:
        for container in containers:
            lines = []
            for i in range(20):
                ts = ns_timestamp(seconds_ago=i * 10)
                lines.append([ts, f"[{container}] Normal operation log line {i} from {host}"])
            push([{
                "stream": {"host": host, "container": container, "unit": f"{container}.service"},
                "values": lines,
            }])


def seed_error_logs():
    """Push error log lines for error_summary testing."""
    print("Seeding error logs...")
    errors = [
        ("test-host-1", "nginx", "ERROR: upstream timed out (110: Connection timed out)"),
        ("test-host-1", "app", "FATAL: database connection pool exhausted"),
        ("test-host-1", "app", "Exception: ValueError in handler /api/users"),
        ("test-host-2", "nginx", "error: SSL handshake failed"),
        ("test-host-2", "db", "PANIC: could not write WAL record"),
        ("test-host-2", "db", "FAIL: replication lag exceeded threshold"),
    ]

    for host, container, msg in errors:
        push([{
            "stream": {"host": host, "container": container},
            "values": [[ns_timestamp(seconds_ago=5), msg]],
        }])


def seed_json_logs():
    """Push JSON-formatted log lines."""
    print("Seeding JSON logs...")
    for i in range(10):
        line = json.dumps({
            "level": "info" if i % 3 != 0 else "error",
            "msg": f"Request processed in {i * 10}ms",
            "method": "GET",
            "path": f"/api/resource/{i}",
            "status": 200 if i % 3 != 0 else 500,
        })
        push([{
            "stream": {"host": "test-host-1", "container": "app", "format": "json"},
            "values": [[ns_timestamp(seconds_ago=i * 5), line]],
        }])


def seed_alert_rules():
    """Create a test alert rule via the rules API."""
    print("Seeding alert rules...")
    rule_yaml = """
name: test-group
interval: 1m
rules:
  - alert: HighErrorRate
    expr: |
      sum(rate({host="test-host-1"} |~ "error" [5m])) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High error rate on test-host-1
"""
    resp = httpx.post(
        f"{LOKI_URL}/loki/api/v1/rules/test-namespace",
        content=rule_yaml.encode(),
        headers={"Content-Type": "application/yaml"},
    )
    if resp.status_code in (200, 202):
        print("  Created alert rule group 'test-group' in namespace 'test-namespace'")
    else:
        print(f"  WARN: rule creation returned {resp.status_code}: {resp.text[:200]}")


def verify_data():
    """Verify seeded data is queryable."""
    print("Verifying data...")
    resp = httpx.get(f"{LOKI_URL}/loki/api/v1/labels")
    if resp.status_code == 200:
        labels = resp.json().get("data", [])
        print(f"  Labels: {labels}")
    else:
        print(f"  WARN: labels query returned {resp.status_code}")

    resp = httpx.get(
        f"{LOKI_URL}/loki/api/v1/query_range",
        params={"query": '{host=~".+"}', "limit": "5"},
    )
    if resp.status_code == 200:
        results = resp.json().get("data", {}).get("result", [])
        total = sum(len(r.get("values", [])) for r in results)
        print(f"  Query returned {len(results)} streams with {total} entries")
    else:
        print(f"  WARN: query returned {resp.status_code}")


if __name__ == "__main__":
    print(f"Seeding Loki at {LOKI_URL}...")
    seed_basic_logs()
    seed_error_logs()
    seed_json_logs()
    seed_alert_rules()
    # Small delay for ingestion
    time.sleep(2)
    verify_data()
    print("Done!")
