import os
import sys

import pytest


def pytest_configure(config):
    root = os.path.dirname(__file__)
    if root not in sys.path:
        sys.path.insert(0, root)
    config.addinivalue_line("markers", "integration: integration tests requiring real infrastructure")


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_INTEGRATION", "0") == "1":
        return
    skip_integration = pytest.mark.skip(reason="integration test; set RUN_INTEGRATION=1 to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
