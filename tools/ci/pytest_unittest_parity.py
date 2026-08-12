from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = ROOT / "tests"


def _flatten(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def _source_path(case: unittest.TestCase) -> Path:
    """Resolve the discovered testcase source without relying on sys.modules retention.

    unittest discovery may evict or replace top-level modules while recursing through
    the tree. The testcase retains its defining module name, which is sufficient to
    resolve the repository source deterministically.
    """

    module_name = case.__class__.__module__
    direct = TEST_ROOT / (module_name.replace(".", "/") + ".py")
    if direct.is_file():
        return direct.resolve()

    basename = module_name.rsplit(".", 1)[-1] + ".py"
    matches = sorted(TEST_ROOT.rglob(basename))
    if len(matches) == 1:
        return matches[0].resolve()

    module = sys.modules.get(module_name)
    source = getattr(module, "__file__", None)
    if source is not None:
        return Path(source).resolve()

    raise RuntimeError(
        f"cannot resolve unique source file for {case.id()}: "
        f"module={module_name!r} matches={[p.as_posix() for p in matches]}"
    )


def _discover() -> tuple[list[unittest.TestCase], list[str]]:
    loader = unittest.TestLoader()
    suite = loader.discover(str(TEST_ROOT))
    if loader.errors:
        for error in loader.errors:
            print(error, file=sys.stderr)
        raise RuntimeError("legacy unittest discovery reported loader errors")
    cases = list(_flatten(suite))
    files = {
        _source_path(case).relative_to(ROOT).as_posix()
        for case in cases
    }
    return cases, sorted(files)


def _expected_keys(cases: list[unittest.TestCase]) -> set[str]:
    return {
        f"{_source_path(case).relative_to(ROOT).as_posix()}::{case.__class__.__name__}::{case._testMethodName}"
        for case in cases
    }


def _pytest_env() -> dict[str, str]:
    env = dict(os.environ)
    env["OVC_PYTEST_LEGACY_ONLY"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    existing = env.get("PYTHONPATH", "")
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src if not existing else os.pathsep.join((src, existing))
    return env


def _base_command(files: list[str]) -> list[str]:
    return [sys.executable, "-m", "pytest", *files]


def run_surface(files: list[str]) -> int:
    completed = subprocess.run(
        [*_base_command(files), "-ra"],
        cwd=ROOT,
        env=_pytest_env(),
        check=False,
    )
    return completed.returncode


def prove_collection(cases: list[unittest.TestCase], files: list[str]) -> int:
    completed = subprocess.run(
        [*_base_command(files), "--collect-only", "-q"],
        cwd=ROOT,
        env=_pytest_env(),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(completed.stdout, end="")
    if completed.returncode != 0:
        print(json.dumps({"status": "FAIL", "reason": "PYTEST_COLLECTION_FAILED", "exit_code": completed.returncode}, sort_keys=True))
        return completed.returncode

    expected = _expected_keys(cases)
    collected = {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().startswith("tests/") and "::" in line
    }
    missing = sorted(expected - collected)
    unexpected = sorted(collected - expected)
    payload = {
        "status": "PASS" if not missing and not unexpected else "FAIL",
        "legacy_unittest_count": len(expected),
        "pytest_legacy_count": len(collected),
        "legacy_source_file_count": len(files),
        "missing": missing,
        "unexpected": unexpected,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute or prove pytest parity for the exact legacy unittest-discovered surface.")
    parser.add_argument("mode", choices=("run", "collect"))
    args = parser.parse_args()
    cases, files = _discover()
    print(json.dumps({"legacy_unittest_count": len(cases), "legacy_source_file_count": len(files)}, sort_keys=True))
    if args.mode == "run":
        return run_surface(files)
    return prove_collection(cases, files)


if __name__ == "__main__":
    raise SystemExit(main())
