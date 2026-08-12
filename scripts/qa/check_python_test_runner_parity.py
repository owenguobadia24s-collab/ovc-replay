from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Iterable

import pytest


ROOT = Path.cwd().resolve()


def _flatten_suite(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten_suite(item)
        else:
            yield item


def _relative_source_path(testcase: unittest.TestCase) -> str:
    module = sys.modules.get(testcase.__class__.__module__)
    source = getattr(module, "__file__", None)
    if source is None:
        raise RuntimeError(f"cannot resolve source for {testcase.id()}")
    return Path(source).resolve().relative_to(ROOT).as_posix()


def _unittest_key(testcase: unittest.TestCase) -> str:
    return "::".join(
        (
            _relative_source_path(testcase),
            testcase.__class__.__qualname__,
            testcase._testMethodName,
        )
    )


def discover_unittest_keys(start_dir: Path) -> set[str]:
    loader = unittest.TestLoader()
    suite = loader.discover(str(start_dir))
    if loader.errors:
        for error in loader.errors:
            print(error, file=sys.stderr)
        raise RuntimeError("unittest discovery reported loader errors")
    return {_unittest_key(test) for test in _flatten_suite(suite)}


class PytestCollectionCapture:
    def __init__(self) -> None:
        self.unittest_keys: set[str] = set()
        self.nodeids: list[str] = []
        self.collection_errors: list[str] = []

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.collection_errors.append(str(report.longrepr))

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            self.nodeids.append(item.nodeid)
            testcase = getattr(item, "_testcase", None)
            if testcase is None:
                continue
            path = Path(str(item.path)).resolve().relative_to(ROOT).as_posix()
            cls = getattr(item, "cls", None)
            class_name = cls.__qualname__ if cls is not None else testcase.__class__.__qualname__
            method_name = getattr(testcase, "_testMethodName", item.name)
            self.unittest_keys.add("::".join((path, class_name, method_name)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove that pytest collects every test discovered by the legacy "
            "unittest runner while also allowing pytest-native tests."
        )
    )
    parser.add_argument("--tests", default="tests", help="test root (default: tests)")
    args = parser.parse_args()

    test_root = Path(args.tests)
    legacy_keys = discover_unittest_keys(test_root)

    capture = PytestCollectionCapture()
    exit_code = pytest.main([str(test_root), "--collect-only", "-q"], plugins=[capture])
    if exit_code != pytest.ExitCode.OK:
        payload = {
            "status": "FAIL",
            "reason": "PYTEST_COLLECTION_FAILED",
            "pytest_exit_code": int(exit_code),
            "collection_errors": capture.collection_errors[-5:],
        }
        print(json.dumps(payload, sort_keys=True))
        return 2

    missing = sorted(legacy_keys - capture.unittest_keys)
    unexpected_unittest = sorted(capture.unittest_keys - legacy_keys)
    payload = {
        "status": "PASS" if not missing else "FAIL",
        "legacy_unittest_count": len(legacy_keys),
        "pytest_unittest_count": len(capture.unittest_keys),
        "pytest_total_collected": len(capture.nodeids),
        "pytest_native_or_other_count": len(capture.nodeids) - len(capture.unittest_keys),
        "missing_unittest_keys": missing,
        "unexpected_pytest_unittest_keys": unexpected_unittest,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
