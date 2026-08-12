from __future__ import annotations

import os


def pytest_collection_modifyitems(config, items):
    """During parity proof, keep only tests backed by unittest.TestCase.

    The hook is inert unless OVC_PYTEST_LEGACY_ONLY=1. This lets pytest execute
    the exact legacy unittest surface without admitting previously dormant
    pytest-native tests into PYT-G1 by accident.
    """

    if os.environ.get("OVC_PYTEST_LEGACY_ONLY") != "1":
        return

    selected = []
    deselected = []
    for item in items:
        if getattr(item, "_testcase", None) is not None:
            selected.append(item)
        else:
            deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected
