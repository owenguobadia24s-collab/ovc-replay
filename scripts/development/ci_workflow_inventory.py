#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_1.json"
WORKFLOW_DIR = ROOT / ".github/workflows"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _workflow_name(text: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^name:\s*(.*?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value
    return ""


def _has_trigger(text: str, trigger: str) -> bool:
    pattern = rf"(?m)^\s{{2,}}{re.escape(trigger)}\s*:"
    if re.search(pattern, text):
        return True
    return bool(re.search(rf"(?m)^on:\s*\[.*\b{re.escape(trigger)}\b.*\]\s*$", text))


def _triggers(text: str, known: list[str]) -> list[str]:
    return [trigger for trigger in known if _has_trigger(text, trigger)]


def classify(path: Path, text: str, policy: dict[str, Any]) -> tuple[str, list[str]]:
    relative = path.relative_to(ROOT).as_posix()
    name = _workflow_name(text)
    lower_name = name.lower()
    lower_text = text.lower()
    approved = set(policy["approved_pull_request_workflows"])

    if _has_trigger(text, "pull_request"):
        if relative not in approved:
            raise ValueError(f"UNEXPECTED_PULL_REQUEST_LISTENER:{relative}")
        return "CURRENT_PR_CI", ["approved pull_request listener"]

    temporary = policy["rules"]["TEMPORARY"]
    basename = path.name.lower()
    for prefix in temporary["path_basename_prefixes"]:
        if basename.startswith(prefix.lower()):
            return "TEMPORARY", [f"basename prefix {prefix}"]
    for prefix in temporary["workflow_name_prefixes_case_insensitive"]:
        if lower_name.startswith(prefix.lower()):
            return "TEMPORARY", [f"workflow name prefix {prefix}"]

    historical = policy["rules"]["HISTORICAL_MANUAL_VERIFICATION"]
    for marker in historical["content_markers_case_insensitive"]:
        if marker.lower() in lower_text:
            return "HISTORICAL_MANUAL_VERIFICATION", [f"content marker {marker}"]

    return "ACTIVE_MANUAL_OPERATION", ["default non-PR operational classification"]


def build_inventory(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    known_triggers = policy["required_trigger_inventory"]
    paths = sorted(
        list((root / ".github/workflows").glob("*.yml"))
        + list((root / ".github/workflows").glob("*.yaml"))
    )
    records: list[dict[str, Any]] = []
    categories: Counter[str] = Counter()
    trigger_counts: Counter[str] = Counter()

    for path in paths:
        text = path.read_text(encoding="utf-8")
        category, reasons = classify(path, text, policy)
        triggers = _triggers(text, known_triggers)
        categories[category] += 1
        trigger_counts.update(triggers)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "workflow_name": _workflow_name(text),
                "category": category,
                "reasons": reasons,
                "triggers": triggers,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )

    expected_categories = set(policy["categories"])
    observed_categories = set(categories)
    unknown_categories = sorted(observed_categories - expected_categories)
    if unknown_categories:
        raise ValueError(f"UNKNOWN_CATEGORIES:{unknown_categories}")

    result = {
        "schema": "ovc-ci-workflow-census/v1",
        "policy_id": policy["policy_id"],
        "programme_id": policy["programme_id"],
        "packet_id": policy["packet_id"],
        "baseline_main_sha": policy["baseline_main_sha"],
        "total_workflow_definitions": len(records),
        "category_counts": dict(sorted(categories.items())),
        "trigger_counts": dict(sorted(trigger_counts.items())),
        "approved_pull_request_workflows": policy["approved_pull_request_workflows"],
        "records": records,
        "authority_delta": "NONE",
        "destructive_actions_performed": False,
    }
    return result


def validate_inventory(inventory: dict[str, Any], policy: dict[str, Any]) -> None:
    expected_total = policy["snapshot"]["expected_repository_workflow_definition_count"]
    if inventory["total_workflow_definitions"] != expected_total:
        raise ValueError(
            f"WORKFLOW_COUNT_DRIFT: expected {expected_total}, observed {inventory['total_workflow_definitions']}"
        )
    pr_records = [record for record in inventory["records"] if "pull_request" in record["triggers"]]
    actual_pr = sorted(record["path"] for record in pr_records)
    expected_pr = sorted(policy["approved_pull_request_workflows"])
    if actual_pr != expected_pr:
        raise ValueError(f"PR_LISTENER_DRIFT: expected {expected_pr}, observed {actual_pr}")
    if inventory["category_counts"].get("CURRENT_PR_CI") != len(expected_pr):
        raise ValueError("CURRENT_PR_CI_COUNT_MISMATCH")
    if sum(inventory["category_counts"].values()) != inventory["total_workflow_definitions"]:
        raise ValueError("CLASSIFICATION_NOT_EXHAUSTIVE")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic OVC CI workflow governance census")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    policy = _load_json(args.policy)
    inventory = build_inventory(ROOT, policy)
    if args.validate:
        validate_inventory(inventory, policy)
    payload = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
