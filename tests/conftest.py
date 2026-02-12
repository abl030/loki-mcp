"""Shared fixtures for integration tests."""

import os
import sys

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

LOKI_URL = os.environ.get("LOKI_TEST_URL", "http://localhost:3100")

# Skip integration tests unless LOKI_TEST_URL is set or --integration flag used
def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests against a live Loki instance",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="Need --integration flag to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def loki_url():
    """Return the Loki URL for integration tests."""
    return LOKI_URL
