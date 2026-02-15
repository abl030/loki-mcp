"""Tests for tool registration in the generated server."""

import re
from pathlib import Path


GENERATED_SERVER = Path(__file__).parent.parent / "generated" / "server.py"


def test_generated_server_exists():
    assert GENERATED_SERVER.exists(), "generated/server.py does not exist — run the generator first"


def test_tool_count():
    code = GENERATED_SERVER.read_text()
    tools = re.findall(r"^async def (loki_\w+)\(", code, re.MULTILINE)
    # 34 direct API + 8 high-level = 42 total
    assert len(tools) == 42, f"Expected 42 tools, found {len(tools)}: {tools}"


def test_all_expected_tools_present():
    code = GENERATED_SERVER.read_text()
    tools = set(re.findall(r"^async def (loki_\w+)\(", code, re.MULTILINE))

    # Direct API tools
    expected_direct = {
        "loki_query_instant", "loki_query_range", "loki_list_labels",
        "loki_list_label_values", "loki_list_series",
        "loki_index_stats", "loki_index_volume", "loki_index_volume_range",
        "loki_detect_patterns",
        "loki_push",
        "loki_list_rules", "loki_get_rules_namespace", "loki_get_rule_group",
        "loki_create_rule_group", "loki_delete_rule_group", "loki_delete_rules_namespace",
        "loki_list_prometheus_rules",
        "loki_create_delete_request", "loki_list_delete_requests", "loki_cancel_delete_request",
        "loki_ready", "loki_metrics", "loki_config", "loki_services",
        "loki_buildinfo", "loki_get_log_level", "loki_set_log_level",
        "loki_flush", "loki_prepare_shutdown_status", "loki_prepare_shutdown",
        "loki_cancel_prepare_shutdown", "loki_shutdown_status", "loki_shutdown",
        "loki_format_query",
    }

    # High-level tools
    expected_highlevel = {
        "loki_search_logs", "loki_error_summary", "loki_volume_by_label",
        "loki_compare_hosts", "loki_get_overview",
        "loki_search_tools", "loki_report_issue", "loki_validate_query",
    }

    expected = expected_direct | expected_highlevel
    missing = expected - tools
    extra = tools - expected
    assert not missing, f"Missing tools: {missing}"
    assert not extra, f"Unexpected tools: {extra}"


def test_mutation_tools_have_confirm():
    code = GENERATED_SERVER.read_text()
    mutation_tools = [
        "loki_push", "loki_create_rule_group", "loki_delete_rule_group",
        "loki_delete_rules_namespace", "loki_create_delete_request",
        "loki_cancel_delete_request", "loki_set_log_level",
        "loki_flush", "loki_prepare_shutdown", "loki_cancel_prepare_shutdown",
        "loki_shutdown",
    ]
    for tool in mutation_tools:
        # Find the function and check it has confirm parameter
        pattern = rf"async def {tool}\([^)]*confirm: bool = False"
        assert re.search(pattern, code, re.DOTALL), f"{tool} missing confirm parameter"


def test_danger_tools_have_warning():
    code = GENERATED_SERVER.read_text()
    danger_tools = [
        "loki_delete_rule_group", "loki_delete_rules_namespace",
        "loki_create_delete_request", "loki_flush",
        "loki_prepare_shutdown", "loki_shutdown",
    ]
    for tool in danger_tools:
        # Find the function and check for danger warning in dry-run
        func_match = re.search(rf"async def {tool}\(.*?(?=async def loki_|\Z)", code, re.DOTALL)
        assert func_match, f"Could not find {tool} function"
        func_code = func_match.group()
        assert "DANGEROUS OPERATION" in func_code, f"{tool} missing danger warning"


def test_module_gating_present():
    code = GENERATED_SERVER.read_text()
    assert "_module_enabled" in code
    assert "LOKI_MODULES" in code


def test_readonly_gating_present():
    code = GENERATED_SERVER.read_text()
    assert "LOKI_READ_ONLY" in code


def test_tool_discovery_dict():
    code = GENERATED_SERVER.read_text()
    assert "_ALL_TOOLS" in code
    # Extract just the dict block
    dict_start = code.index("_ALL_TOOLS: dict[str, str] = {")
    dict_end = code.index("}", dict_start) + 1
    dict_block = code[dict_start:dict_end]
    tool_entries = re.findall(r'"loki_\w+":', dict_block)
    assert len(tool_entries) == 42


def test_exclude_parameter_on_search_tools():
    """Verify exclude: str = '' exists on search_logs, error_summary, compare_hosts."""
    code = GENERATED_SERVER.read_text()
    for tool in ["loki_search_logs", "loki_error_summary", "loki_compare_hosts"]:
        pattern = rf"async def {tool}\([^)]*exclude: str = \"\""
        assert re.search(pattern, code, re.DOTALL), f"{tool} missing exclude parameter"


def test_stats_stripping_in_unwrap():
    """Verify _unwrap_loki_response strips the stats key."""
    code = GENERATED_SERVER.read_text()
    # Find the _unwrap_loki_response function
    func_match = re.search(r"def _unwrap_loki_response\(.*?(?=\ndef )", code, re.DOTALL)
    assert func_match, "Could not find _unwrap_loki_response"
    func_code = func_match.group()
    assert 'k != "stats"' in func_code, "stats stripping logic missing from _unwrap_loki_response"


def test_timestamp_formatting_helpers():
    """Verify _format_ns_timestamp and _format_log_values exist in generated code."""
    code = GENERATED_SERVER.read_text()
    assert "def _format_ns_timestamp(ns_str: str) -> str:" in code
    assert "def _format_log_values(result: Any) -> None:" in code


def test_cross_reference_in_volume_by_label():
    """Verify loki_volume_by_label docstring mentions loki_index_volume."""
    code = GENERATED_SERVER.read_text()
    func_match = re.search(
        r"async def loki_volume_by_label\(.*?(?=async def loki_|\Z)", code, re.DOTALL
    )
    assert func_match, "Could not find loki_volume_by_label"
    func_code = func_match.group()
    assert "loki_index_volume" in func_code, "loki_volume_by_label missing cross-reference to loki_index_volume"
