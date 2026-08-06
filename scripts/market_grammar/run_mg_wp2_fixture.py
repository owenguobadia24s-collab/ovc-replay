#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ovc.opt_b.market_grammar.episode_ledger import build_episode_ledger

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "fixtures/market_grammar/wp2/c2e_ledger_cases.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("fixture root must be an object")
    return value


def run(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load(path)
    valid_results: list[dict[str, Any]] = []
    invalid_results: list[dict[str, Any]] = []
    for case in fixture["valid_cases"]:
        ledger = build_episode_ledger(case["records"], build_cutoff=case["build_cutoff"])
        valid_results.append({
            "case_id": case["case_id"],
            "ledger_id": ledger.ledger_id,
            "episode_count": len(ledger.episodes),
            "not_evaluable_count": len(ledger.not_evaluable),
            "statuses": [item.status.value for item in ledger.episodes],
            "boundary_causes": [item.boundary_cause.value for item in ledger.episodes],
            "phase_kinds": [[phase.phase_kind.value for phase in item.phases] for item in ledger.episodes],
            "not_evaluable_statuses": [item.computability_status.value for item in ledger.not_evaluable],
        })
    for case in fixture["invalid_cases"]:
        try:
            build_episode_ledger(case["records"], build_cutoff=case["build_cutoff"])
        except ValueError as exc:
            invalid_results.append({"case_id": case["case_id"], "error": str(exc)})
        else:
            raise AssertionError(f"invalid case did not fail: {case['case_id']}")
    return {
        "schema": "ovc-mg-wp2-fixture-result/v1",
        "authority": fixture["authority"],
        "policy_id": fixture["policy_id"],
        "valid_results": valid_results,
        "invalid_results": invalid_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    print(json.dumps(run(args.fixture), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
