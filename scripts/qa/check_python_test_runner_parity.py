from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from typing import Iterable

import pytest


def _flatten_suite(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten_suite(item)
        else:
            yield item


def discover_unittest_ids(start_dir: Path) -> set[str]:
    loader = unittest.TestLoader()
    suite = loader.discover(str(start_dir))
    if loader.errors:
        for error in loader.errors:
            print(error, file=sys.stderr)
        raise RuntimeError("unittest discovery reported loader errors")
    return {test.id() for test in _flatten_suite(suite)}


class PytestCollectionCapture:
    def __init__(self) -> None:
        self.unittest_ids: set[str] = set()
        self.nodeids: list[str] = []

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            self.nodeids.append(item.nodeid)
            testcase = getattr(item, "_testcase", None)
            if testcase is not None:
                self.unittest_ids.add(testcase.id())


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
    legacy_ids = discover_unittest_ids(test_root)

    capture = PytestCollectionCapture()
    exit_code = pytest.main([str(test_root), "--collect-only", "-q"], plugins=[capture])
    if exit_code != pytest.ExitCode.OK:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "PYTEST_COLLECTION_FAILED",
                    "pytest_exit_code": int(exit_code),
                },
                sort_keys=True,
            )
        )
        return 2

    missing = sorted(legacy_ids - capture.unittest_ids)
    unexpected_unittest = sorted(capture.unittest_ids - legacy_ids)
    payload = {
        "status": "PASS" if not missing else "FAIL",
        "legacy_unittest_count": len(legacy_ids),
        "pytest_unittest_count": len(capture.unittest_ids),
        "pytest_total_collected": len(capture.nodeids),
        "pytest_native_or_other_count": len(capture.nodeids) - len(capture.unittest_ids),
        "missing_unittest_ids": missing,
        "unexpected_pytest_unittest_ids": unexpected_unittest,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
