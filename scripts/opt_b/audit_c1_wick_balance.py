from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ovc.opt_b.c1.formulas import C1_IMPLEMENTATION_ID, FORMULA_REGISTRY_ID, calculate_wick_balance

getcontext().prec = 34


def _text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _record_files(root: Path) -> Iterable[Path]:
    records = root / "records" if (root / "records").is_dir() else root
    return sorted(records.rglob("*.jsonl.gz"))


def _scope(record: dict[str, Any]) -> str:
    return f"{record.get('clock', 'UNKNOWN')}:{record.get('price_side', record.get('side', 'UNKNOWN'))}"


def audit_role(role: str, root: Path) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    scopes: dict[str, Counter[str]] = {}
    files: list[dict[str, Any]] = []
    mismatches: list[dict[str, str]] = []

    for path in _record_files(root):
        file_counter: Counter[str] = Counter()
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                measurements = record["measurements"]
                range_abs = Decimal(str(measurements["range_abs"]))
                upper = Decimal(str(measurements["upper_wick_abs"]))
                lower = Decimal(str(measurements["lower_wick_abs"]))
                actual = measurements.get("wick_balance")
                expected = _text(calculate_wick_balance(upper, lower, range_abs))
                wrong_sign = _text(None if range_abs == 0 else (lower - upper) / range_abs)
                scope = _scope(record)
                scope_counter = scopes.setdefault(scope, Counter())

                counters["records"] += 1
                file_counter["records"] += 1
                scope_counter["records"] += 1
                if actual is None:
                    category = "null"
                elif Decimal(str(actual)) == 0:
                    category = "zero"
                else:
                    category = "nonzero"
                counters[category] += 1
                file_counter[category] += 1
                scope_counter[category] += 1

                if actual != expected:
                    counters["active_mismatch"] += 1
                    file_counter["active_mismatch"] += 1
                    scope_counter["active_mismatch"] += 1
                    if len(mismatches) < 20:
                        mismatches.append(
                            {
                                "path": path.as_posix(),
                                "line": str(line_number),
                                "record_id": str(record.get("record_id")),
                                "actual": str(actual),
                                "expected": str(expected),
                            }
                        )
                if actual != wrong_sign:
                    counters["counterfactual_wrong_library_divergence"] += 1
                    file_counter["counterfactual_wrong_library_divergence"] += 1
                    scope_counter["counterfactual_wrong_library_divergence"] += 1

        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                **dict(sorted(file_counter.items())),
            }
        )

    return {
        "role": role,
        "root_name": root.name,
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "implementation_id": C1_IMPLEMENTATION_ID,
        "counts": dict(sorted(counters.items())),
        "scopes": {key: dict(sorted(value.items())) for key, value in sorted(scopes.items())},
        "files": files,
        "file_count": len(files),
        "active_mismatch_examples": mismatches,
        "status": "PASS_ACTIVE_RELEASE_MATCHES_FROZEN_REGISTRY" if counters["active_mismatch"] == 0 else "BLOCK_ACTIVE_RELEASE_MISMATCH",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roles = [
        audit_role("DISCOVERY", args.discovery_root),
        audit_role("DEVELOPMENT", args.development_root),
    ]
    totals: Counter[str] = Counter()
    for role in roles:
        totals.update(role["counts"])
    report = {
        "schema": "ovc-c1-wick-balance-impact-audit/v1",
        "programme_id": "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1",
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "implementation_id": C1_IMPLEMENTATION_ID,
        "roles": roles,
        "totals": dict(sorted(totals.items())),
        "active_affected_record_count": totals["active_mismatch"],
        "active_affected_file_count": sum(
            1 for role in roles for item in role["files"] if item.get("active_mismatch", 0)
        ),
        "counterfactual_wrong_library_divergence_record_count": totals["counterfactual_wrong_library_divergence"],
        "status": "PASS_ACTIVE_RELEASES_CORRECT_IMPLEMENTATION_DRIFT_CONFIRMED" if totals["active_mismatch"] == 0 else "BLOCK_ACTIVE_RELEASE_CORRECTION_REQUIRED",
        "authority": {
            "release_mutation": "NONE",
            "selector_mutation": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "c2_mutation": "NONE",
            "pattern_discovery_canonical_append": "NONE",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(_canonical(report))
    if totals["active_mismatch"]:
        raise SystemExit("active C1 release does not match frozen wick-balance formula")


if __name__ == "__main__":
    main()
