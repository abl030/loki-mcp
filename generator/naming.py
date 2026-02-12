"""Tool naming conventions and module definitions."""

from __future__ import annotations

# All valid modules
MODULES = {
    "query",
    "index",
    "patterns",
    "ingest",
    "rules",
    "delete",
    "status",
    "admin",
    "format",
}

# Modules whose mutation tools are stripped in read-only mode
MUTATION_MODULES = {"ingest", "rules", "delete", "admin"}

# Python type mapping from spec types
TYPE_MAP: dict[str, str] = {
    "str": "str",
    "int": "int",
    "list": "list",
    "bool": "bool",
    "float": "float",
}


def python_type(spec_type: str) -> str:
    """Convert spec type string to Python type annotation."""
    return TYPE_MAP.get(spec_type, "str")


def python_default(param_type: str, default) -> str:
    """Convert a default value to its Python repr."""
    if default is None:
        return '""' if param_type == "str" else "0" if param_type == "int" else "None"
    if isinstance(default, str):
        return f'"{default}"'
    return repr(default)
