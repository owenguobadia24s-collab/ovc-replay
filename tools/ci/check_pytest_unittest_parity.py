#!/usr/bin/env python3
"""Prove that pytest preserves collection of the legacy unittest suite.

The migration rule is intentionally asymmetric: every test currently discovered by
``python -m unittest discover -s tests`` must also be collected by pytest. Pytest may
collect additional native pytest tests. Behavioural parity is proved by CI running
both complete runners on the same commit before this checker executes.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = ROOT / "tests"


def _iter_tests(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            if not isinstance(item, unittest.TestCase):
                raise RuntimeError(f"UNSUPPORTED_UNITTEST_CASE_TYPE:{type(item)!r}")
            yield item


def _relative(path: str | os.PathLike[str]) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def _legacy_key(test: unittest.TestCase) -> str:
    cls = test.__class__
    if cls.__module__ == "unittest.loader" and cls.__name__ == "_FailedTest":
        raise RuntimeError(f"UNITTEST_DISCOVERY_FAILED:{test.id()}")
    module = sys.modules.get(cls.__module__)
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise RuntimeError(f"UNITTEST_MODULE_FILE_MISSING:{test.id()}")
    method = getattr(test, "_testMethodName", None)
    if not method:
        raise RuntimeError(f"UNITTEST_METHOD_NAME_MISSING:{test.id()}")
    return f"{_relative(module_file)}::{cls.__qualname__}::{method}"


def collect_legacy_unittest_keys() -> set[str]:
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        suite = unittest.defaultTestLoader.discover("tests")
        return {_legacy_key(test) for test in _iter_tests(suite)}
    finally:
        os.chdir(previous)


class _PytestCollector:
    def __init__(self) -> None:
        self.unittest_keys: set[str] = set()
        self.total_items = 0

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.total_items = len(session.items)
        for item in session.items:
            cls = getattr(item, "cls", None)
            if not isinstance(cls, type) or not issubclass(cls, unittest.TestCase):
                continue
            method = getattr(item, "originalname", None) or item.name
            self.unittest_keys.add(
                f"{_relative(str(item.path))}::{cls.__qualname__}::{method}"
            )


def collect_pytest_unittest_keys() -> tuple[set[str], int]:
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    plugin = _PytestCollector()
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        exit_code = pytest.main(["--collect-only", "-q", "tests"], plugins=[plugin])
    finally:
        os.chdir(previous)
    if exit_code != pytest.ExitCode.OK:
        raise RuntimeError(f"PYTEST_COLLECTION_FAILED:{int(exit_code)}")
    return plugin.unittest_keys, plugin.total_items


def main() -> int:
    legacy = collect_legacy_unittest_keys()
    pytest_unittest, pytest_total = collect_pytest_unittest_keys()
    missing = sorted(legacy - pytest_unittest)
    additional = sorted(pytest_unittest - legacy)
    receipt = {
        "schema": "ovc-python-test-runner-parity/v1",
        "status": "PASS" if not missing else "FAIL",
        "legacy_unittest_collected": len(legacy),
        "pytest_unittest_collected": len(pytest_unittest),
        "pytest_total_collected": pytest_total,
        "missing_legacy_unittest_cases": missing,
        "additional_unittest_cases_collected_by_pytest": additional,
        "rule": "legacy_unittest_set_must_be_subset_of_pytest_collection",
    }
    print(json.dumps(receipt, sort_keys=True))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
