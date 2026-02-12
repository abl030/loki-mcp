"""Build Jinja2 template context from the loaded inventory."""

from __future__ import annotations

from generator.loader import Endpoint, LokiInventory, Parameter
from generator.naming import MODULES, python_default, python_type


def _build_param_context(param: Parameter) -> dict:
    """Build template context for a single parameter."""
    desc = param.description
    if param.enum:
        desc += f". Valid values: {', '.join(repr(v) for v in param.enum)}"
    return {
        "name": param.name,
        "type": python_type(param.type),
        "spec_type": param.type,
        "required": param.required,
        "description": desc,
        "default": python_default(param.type, param.default),
        "has_default": param.default is not None,
        "enum": param.enum,
    }


def _build_endpoint_context(ep: Endpoint) -> dict:
    """Build template context for a single endpoint."""
    required_params = [p for p in ep.parameters if p.required]
    optional_params = [p for p in ep.parameters if not p.required]

    # Path parameters are interpolated into the URL
    path_params = [p for p in ep.parameters if f"{{{p.name}}}" in ep.path]
    path_param_names = {p.name for p in path_params}

    # Query/body parameters are everything else
    query_params = [p for p in ep.parameters if p.name not in path_param_names]

    # Determine if this is a text response (not JSON)
    is_text_response = ep.path in {"/ready", "/metrics", "/config", "/services"}
    # Form-encoded body
    is_form_encoded = ep.id == "set_log_level"
    # YAML body
    is_yaml_body = ep.id == "create_rule_group"
    # No-content response
    is_no_content = ep.method in ("POST", "DELETE") and not ep.response_fields

    return {
        "id": ep.id,
        "module": ep.module,
        "method": ep.method,
        "path": ep.path,
        "tool_name": ep.tool_name,
        "description": ep.description,
        "mutation": ep.mutation,
        "danger": ep.danger,
        "notes": ep.notes,
        "followup": ep.followup,
        "parameters": [_build_param_context(p) for p in ep.parameters],
        "required_params": [_build_param_context(p) for p in required_params],
        "optional_params": [_build_param_context(p) for p in optional_params],
        "path_params": [_build_param_context(p) for p in path_params],
        "query_params": [_build_param_context(p) for p in query_params],
        "response_fields": ep.response_fields,
        "is_text_response": is_text_response,
        "is_form_encoded": is_form_encoded,
        "is_yaml_body": is_yaml_body,
        "is_no_content": is_no_content,
    }


def build_context(inventory: LokiInventory) -> dict:
    """Build the full Jinja2 template context."""
    # Group endpoints by module
    endpoints_by_module: dict[str, list[dict]] = {m: [] for m in MODULES}
    all_endpoints = []

    for ep in inventory.endpoints:
        ep_ctx = _build_endpoint_context(ep)
        endpoints_by_module.setdefault(ep.module, []).append(ep_ctx)
        all_endpoints.append(ep_ctx)

    # High-level tools
    high_level_tools = [
        {
            "tool_name": t.tool_name,
            "description": t.description,
            "module": t.module,
        }
        for t in inventory.high_level_tools
    ]

    # Module metadata
    modules = {
        name: {
            "name": name,
            "description": info.description,
            "endpoint_count": info.endpoint_count,
        }
        for name, info in inventory.modules.items()
    }

    tool_count = len(all_endpoints) + len(high_level_tools)

    return {
        "loki_version": inventory.loki_version,
        "endpoints": all_endpoints,
        "endpoints_by_module": endpoints_by_module,
        "high_level_tools": high_level_tools,
        "modules": modules,
        "tool_count": tool_count,
    }
