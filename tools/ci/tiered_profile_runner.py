from __future__ import annotations

import argparse
import json
from pathlib import Path
import py_compile
import subprocess
import sys

from ovc.development.identity import normalize_relative_path


ROOT = Path(__file__).resolve().parents[2]
PROFILES = {"FAST", "PACKET", "FINAL_HEAD"}


class TieredProfileError(RuntimeError):
    """Raised when a changed-path packet cannot receive bounded assurance."""


def _changed_paths(path: Path) -> tuple[str, ...]:
    try:
        rows = tuple(
            sorted(
                {
                    normalize_relative_path(row.strip())
                    for row in path.read_text(encoding="utf-8").splitlines()
                    if row.strip()
                }
            )
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise TieredProfileError(f"TIERED_CHANGED_PATHS_INVALID:{exc}") from exc
    if not rows:
        raise TieredProfileError("TIERED_CHANGED_PATHS_EMPTY")
    return rows


def _is_packet_test(path: str) -> bool:
    value = Path(path)
    return path.startswith("tests/") and value.suffix == ".py" and value.name.startswith("test")


def _is_executable_python(path: str) -> bool:
    return path.endswith(".py") and path.startswith(("src/", "scripts/", "tools/"))


def build_plan(profile: str, changed_paths: tuple[str, ...]) -> dict[str, object]:
    if profile not in PROFILES:
        raise TieredProfileError(f"TIERED_PROFILE_INVALID:{profile}")
    present = tuple(path for path in changed_paths if (ROOT / path).is_file())
    python_paths = tuple(path for path in present if path.endswith(".py"))
    json_paths = tuple(path for path in present if path.endswith(".json"))
    packet_tests = tuple(path for path in present if _is_packet_test(path))
    executable = tuple(path for path in present if _is_executable_python(path))

    if profile == "FAST" and (packet_tests or executable):
        raise TieredProfileError("FAST_PROFILE_EXECUTABLE_OR_TEST_MUTATION")
    if profile == "PACKET" and executable and not packet_tests:
        raise TieredProfileError("PACKET_EXECUTABLE_CHANGE_REQUIRES_CHANGED_PACKET_TEST")

    pytest_targets: list[str] = []
    if profile in {"PACKET", "FINAL_HEAD"}:
        pytest_targets.extend(packet_tests)
        pytest_targets.append("tests/authority")

    return {
        "schema": "ovc-tiered-profile-execution-plan/v1",
        "profile": profile,
        "changed_paths": list(changed_paths),
        "python_validation_paths": list(python_paths),
        "json_validation_paths": list(json_paths),
        "packet_test_paths": list(packet_tests),
        "pytest_targets": sorted(set(pytest_targets)),
        "complete_sweep_executed": False,
        "pytest_unittest_parity_executed": False,
    }


def execute_plan(plan: dict[str, object]) -> int:
    for path in plan["python_validation_paths"]:
        py_compile.compile(str(ROOT / str(path)), doraise=True)
    for path in plan["json_validation_paths"]:
        json.loads((ROOT / str(path)).read_text(encoding="utf-8"))

    targets = [str(path) for path in plan["pytest_targets"]]
    if targets:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q", "--tb=short"],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode != 0:
            return completed.returncode
    print("OVC_TIERED_PROFILE_RESULT=" + json.dumps(plan, sort_keys=True, separators=(",", ":")))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the bounded OVC tiered blocking profile.")
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--changed-paths-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        plan = build_plan(args.profile, _changed_paths(args.changed_paths_file))
        return execute_plan(plan)
    except (TieredProfileError, OSError, UnicodeError, json.JSONDecodeError, py_compile.PyCompileError) as exc:
        print(f"OVC_TIERED_PROFILE_BLOCKED={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
