"""Load endpoint-inventory.json into structured data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Parameter:
    name: str
    type: str
    required: bool
    description: str
    default: str | int | None = None
    enum: list[str] | None = None


@dataclass
class Endpoint:
    id: str
    module: str
    method: str
    path: str
    tool_name: str
    description: str
    mutation: bool
    danger: bool
    parameters: list[Parameter] = field(default_factory=list)
    response_fields: list[str] = field(default_factory=list)
    notes: str = ""
    followup: str = ""
    filterable: bool = False
    filter_path: str | None = None
    filter_label_key: str | None = None
    known_fields: list[str] = field(default_factory=list)


@dataclass
class HighLevelTool:
    tool_name: str
    description: str
    module: str | None


@dataclass
class ModuleInfo:
    name: str
    description: str
    endpoint_count: int


@dataclass
class LokiInventory:
    loki_version: str
    endpoints: list[Endpoint]
    high_level_tools: list[HighLevelTool]
    modules: dict[str, ModuleInfo]


def load_inventory(inventory_path: Path) -> LokiInventory:
    """Parse endpoint-inventory.json into structured data."""
    raw = json.loads(inventory_path.read_text())

    endpoints = []
    for ep in raw.get("endpoints", []):
        params = [
            Parameter(
                name=p["name"],
                type=p["type"],
                required=p["required"],
                description=p.get("description", ""),
                default=p.get("default"),
                enum=p.get("enum"),
            )
            for p in ep.get("parameters", [])
        ]
        endpoints.append(
            Endpoint(
                id=ep["id"],
                module=ep["module"],
                method=ep["method"],
                path=ep["path"],
                tool_name=ep["tool_name"],
                description=ep["description"],
                mutation=ep.get("mutation", False),
                danger=ep.get("danger", False),
                parameters=params,
                response_fields=ep.get("response_fields", []),
                notes=ep.get("notes", ""),
                followup=ep.get("followup", ""),
                filterable=ep.get("filterable", False),
                filter_path=ep.get("filter_path"),
                filter_label_key=ep.get("filter_label_key"),
                known_fields=ep.get("known_fields", []),
            )
        )

    high_level_tools = [
        HighLevelTool(
            tool_name=t["tool_name"],
            description=t["description"],
            module=t.get("module"),
        )
        for t in raw.get("high_level_tools", [])
    ]

    modules = {}
    for name, info in raw.get("modules", {}).items():
        modules[name] = ModuleInfo(
            name=name,
            description=info["description"],
            endpoint_count=info["endpoint_count"],
        )

    return LokiInventory(
        loki_version=raw.get("loki_version", "unknown"),
        endpoints=endpoints,
        high_level_tools=high_level_tools,
        modules=modules,
    )
