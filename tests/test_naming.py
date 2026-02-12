"""Tests for tool naming conventions."""

from generator.naming import MODULES, python_default, python_type


def test_all_modules_defined():
    expected = {"query", "index", "patterns", "ingest", "rules", "delete", "status", "admin", "format"}
    assert MODULES == expected


def test_python_type_mapping():
    assert python_type("str") == "str"
    assert python_type("int") == "int"
    assert python_type("list") == "list"
    assert python_type("bool") == "bool"
    assert python_type("unknown") == "str"  # fallback


def test_python_default_str():
    assert python_default("str", None) == '""'
    assert python_default("str", "backward") == '"backward"'


def test_python_default_int():
    assert python_default("int", None) == "0"
    assert python_default("int", 100) == "100"
