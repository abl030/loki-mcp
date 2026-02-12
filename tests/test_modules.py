"""Tests for module gating and context building."""

import json
from pathlib import Path

from generator.context_builder import build_context
from generator.loader import load_inventory

SPEC_PATH = Path(__file__).parent.parent / "spec" / "endpoint-inventory.json"


def test_load_inventory():
    inv = load_inventory(SPEC_PATH)
    assert inv.loki_version == "3.x"
    assert len(inv.endpoints) == 34
    assert len(inv.high_level_tools) == 8
    assert len(inv.modules) == 9


def test_build_context():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    assert ctx["tool_count"] == 42
    assert len(ctx["endpoints"]) == 34
    assert len(ctx["high_level_tools"]) == 8


def test_endpoints_by_module():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    by_mod = ctx["endpoints_by_module"]
    assert len(by_mod["query"]) == 5
    assert len(by_mod["index"]) == 3
    assert len(by_mod["patterns"]) == 1
    assert len(by_mod["ingest"]) == 1
    assert len(by_mod["rules"]) == 7
    assert len(by_mod["delete"]) == 3
    assert len(by_mod["status"]) == 7
    assert len(by_mod["admin"]) == 6
    assert len(by_mod["format"]) == 1


def test_mutation_flags():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    mutations = [ep for ep in ctx["endpoints"] if ep["mutation"]]
    # push, create_rule_group, delete_rule_group, delete_rules_namespace,
    # create_delete_request, cancel_delete_request, set_log_level,
    # flush, prepare_shutdown, cancel_prepare_shutdown, shutdown
    assert len(mutations) == 11


def test_danger_flags():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    dangerous = [ep for ep in ctx["endpoints"] if ep["danger"]]
    # delete_rule_group, delete_rules_namespace, create_delete_request,
    # flush, prepare_shutdown, shutdown
    assert len(dangerous) == 6


def test_all_tools_have_loki_prefix():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    for ep in ctx["endpoints"]:
        assert ep["tool_name"].startswith("loki_"), f"{ep['tool_name']} missing loki_ prefix"
    for hl in ctx["high_level_tools"]:
        assert hl["tool_name"].startswith("loki_"), f"{hl['tool_name']} missing loki_ prefix"


def test_path_params_detected():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    label_values = next(ep for ep in ctx["endpoints"] if ep["id"] == "list_label_values")
    assert len(label_values["path_params"]) == 1
    assert label_values["path_params"][0]["name"] == "name"

    rule_group = next(ep for ep in ctx["endpoints"] if ep["id"] == "get_rule_group")
    assert len(rule_group["path_params"]) == 2


def test_text_response_endpoints():
    inv = load_inventory(SPEC_PATH)
    ctx = build_context(inv)
    text_eps = [ep for ep in ctx["endpoints"] if ep["is_text_response"]]
    text_ids = {ep["id"] for ep in text_eps}
    assert text_ids == {"ready", "metrics", "config", "services"}
