"""Deterministic changed-file impact selection for governed test profiles."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .identity import canonical_sha256, normalize_relative_path


class TestSelectionError(ValueError):
    """Raised when a test registry or selection request is unsafe or ambiguous."""


_PROFILE_ORDER = {"FAST": 1, "PACKET": 2, "FINAL_HEAD": 3}
_STAGES = {"CHANGE", "FINAL_HEAD", "GATE_REPLAY"}


@dataclass(frozen=True)
class TestProfile:
    name: str
    commands: tuple[str, ...]


@dataclass(frozen=True)
class TestRule:
    rule_id: str
    pattern: str
    priority: int
    owner: str
    minimum_profile: str
    commands: tuple[str, ...]
    retained_checks: tuple[str, ...]

    def matches(self, path: str) -> bool:
        return fnmatchcase(path, self.pattern)


@dataclass(frozen=True)
class TestProfileRegistry:
    registry_id: str
    programme_id: str
    profile_order: tuple[str, ...]
    profiles: Mapping[str, TestProfile]
    rules: tuple[TestRule, ...]
    unknown_path_policy: str
    ambiguous_dependency_policy: str
    final_assurance: Mapping[str, Any]
    registry_hash: str


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TestSelectionError(f"{field} must be a non-empty string")
    return value


def _string_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise TestSelectionError(f"{field} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    result: list[str] = []
    for item in value:
        result.append(_non_empty_string(item, field))
    if len(result) != len(set(result)):
        raise TestSelectionError(f"{field} contains duplicates")
    return tuple(result)


def parse_test_profile_registry(obj: Mapping[str, Any]) -> TestProfileRegistry:
    allowed = {
        "schema", "registry_id", "programme_id", "profile_order", "profiles", "rules",
        "unknown_path_policy", "ambiguous_dependency_policy", "final_assurance",
    }
    if set(obj) != allowed:
        raise TestSelectionError(f"registry fields mismatch: {sorted(set(obj) ^ allowed)}")
    if obj.get("schema") != "ovc-test-profile-registry/v1":
        raise TestSelectionError("unsupported test profile registry schema")

    profile_order = _string_list(obj.get("profile_order"), "profile_order")
    if profile_order != ("FAST", "PACKET", "FINAL_HEAD"):
        raise TestSelectionError("profile_order must be FAST, PACKET, FINAL_HEAD")

    raw_profiles = obj.get("profiles")
    if not isinstance(raw_profiles, dict) or set(raw_profiles) != set(profile_order):
        raise TestSelectionError("profiles must define exactly FAST, PACKET and FINAL_HEAD")
    profiles: dict[str, TestProfile] = {}
    for name in profile_order:
        row = raw_profiles[name]
        if not isinstance(row, dict) or set(row) != {"commands"}:
            raise TestSelectionError(f"invalid profile definition for {name}")
        profiles[name] = TestProfile(name, _string_list(row["commands"], f"profiles.{name}.commands"))

    raw_rules = obj.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise TestSelectionError("rules must be a non-empty list")
    rules: list[TestRule] = []
    rule_ids: set[str] = set()
    patterns_and_priorities: set[tuple[str, int]] = set()
    for raw in raw_rules:
        if not isinstance(raw, dict):
            raise TestSelectionError("rule entries must be objects")
        required = {"rule_id", "pattern", "priority", "owner", "minimum_profile", "commands", "retained_checks"}
        if set(raw) != required:
            raise TestSelectionError("rule fields mismatch")
        rule_id = _non_empty_string(raw["rule_id"], "rule_id")
        pattern = _non_empty_string(raw["pattern"], "pattern").replace("\\", "/")
        if pattern.startswith("/") or ":" in pattern.split("/", 1)[0] or ".." in pattern.split("/"):
            raise TestSelectionError(f"unsafe rule pattern: {pattern}")
        priority = raw["priority"]
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
            raise TestSelectionError("rule priority must be a non-negative integer")
        minimum_profile = _non_empty_string(raw["minimum_profile"], "minimum_profile")
        if minimum_profile not in _PROFILE_ORDER:
            raise TestSelectionError(f"unknown minimum profile: {minimum_profile}")
        key = (pattern, priority)
        if rule_id in rule_ids or key in patterns_and_priorities:
            raise TestSelectionError("duplicate rule ID or pattern/priority")
        rule_ids.add(rule_id)
        patterns_and_priorities.add(key)
        rules.append(TestRule(
            rule_id=rule_id,
            pattern=pattern,
            priority=priority,
            owner=_non_empty_string(raw["owner"], "owner"),
            minimum_profile=minimum_profile,
            commands=_string_list(raw["commands"], "rule.commands"),
            retained_checks=_string_list(raw["retained_checks"], "rule.retained_checks"),
        ))

    unknown = obj.get("unknown_path_policy")
    if unknown != "FINAL_HEAD":
        raise TestSelectionError("unknown_path_policy must be FINAL_HEAD")
    ambiguous = obj.get("ambiguous_dependency_policy")
    if ambiguous != "BLOCK_AND_REQUIRE_PROFILE_CORRECTION":
        raise TestSelectionError("unsupported ambiguous dependency policy")

    assurance = obj.get("final_assurance")
    required_assurance = {
        "required_on_stable_pr_head": True,
        "required_after_base_change": True,
        "complete_repository_suite": True,
        "gate_replay_substitution": "PROHIBITED",
        "local_success_substitutes_remote_required_check": False,
    }
    if assurance != required_assurance:
        raise TestSelectionError("final assurance may not be weakened")

    return TestProfileRegistry(
        registry_id=_non_empty_string(obj["registry_id"], "registry_id"),
        programme_id=_non_empty_string(obj["programme_id"], "programme_id"),
        profile_order=profile_order,
        profiles=profiles,
        rules=tuple(sorted(rules, key=lambda row: (row.pattern, -row.priority, row.rule_id))),
        unknown_path_policy=unknown,
        ambiguous_dependency_policy=ambiguous,
        final_assurance=dict(assurance),
        registry_hash=canonical_sha256(obj, role="TEST_PROFILE_REGISTRY"),
    )


def load_test_profile_registry(path: Path) -> TestProfileRegistry:
    if path.suffix.lower() != ".json":
        raise TestSelectionError("runtime test profile registries must use JSON")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TestSelectionError(f"cannot load test profile registry: {exc}") from exc
    if not isinstance(value, dict):
        raise TestSelectionError("test profile registry root must be an object")
    return parse_test_profile_registry(value)


def _normalized_changed_paths(changed_paths: Iterable[str]) -> tuple[str, ...]:
    try:
        normalized = tuple(sorted({normalize_relative_path(path) for path in changed_paths}))
    except ValueError as exc:
        raise TestSelectionError(f"unsafe changed path: {exc}") from exc
    if not normalized:
        raise TestSelectionError("changed-file inventory is empty")
    return normalized


def _ambiguous(top_rules: list[TestRule]) -> bool:
    definitions = {
        (row.owner, row.minimum_profile, row.commands, row.retained_checks)
        for row in top_rules
    }
    return len(definitions) > 1


def select_test_manifest(
    changed_paths: Iterable[str],
    registry: TestProfileRegistry,
    *,
    stage: str = "CHANGE",
    gate_id: str | None = None,
    gate_command: str | None = None,
) -> dict[str, Any]:
    """Select the deterministic minimum test profile without weakening final assurance."""
    if stage not in _STAGES:
        raise TestSelectionError(f"unsupported selection stage: {stage}")
    paths = _normalized_changed_paths(changed_paths)
    if stage == "GATE_REPLAY":
        gate_id = _non_empty_string(gate_id, "gate_id")
        gate_command = _non_empty_string(gate_command, "gate_command")
    elif gate_id is not None or gate_command is not None:
        raise TestSelectionError("gate replay fields are permitted only for GATE_REPLAY")

    matched_rows: list[dict[str, Any]] = []
    unknown_paths: list[str] = []
    ambiguous_paths: list[str] = []
    minimum_profiles: list[str] = []
    commands: set[str] = set()
    retained_checks: set[str] = set()

    for path in paths:
        matches = [rule for rule in registry.rules if rule.matches(path)]
        if not matches:
            unknown_paths.append(path)
            minimum_profiles.append("FINAL_HEAD")
            commands.update(registry.profiles["FINAL_HEAD"].commands)
            retained_checks.add("unknown-path-final-head-escalation")
            continue
        highest = max(rule.priority for rule in matches)
        top = [rule for rule in matches if rule.priority == highest]
        if _ambiguous(top):
            ambiguous_paths.append(path)
            continue
        rule = sorted(top, key=lambda row: row.rule_id)[0]
        minimum_profiles.append(rule.minimum_profile)
        commands.update(rule.commands)
        retained_checks.update(rule.retained_checks)
        matched_rows.append({
            "path": path,
            "rule_id": rule.rule_id,
            "pattern": rule.pattern,
            "priority": rule.priority,
            "owner": rule.owner,
            "minimum_profile": rule.minimum_profile,
        })

    blockers = [f"AMBIGUOUS_PATH:{path}" for path in sorted(ambiguous_paths)]
    status = "BLOCK" if blockers else "PASS"

    if stage == "GATE_REPLAY":
        selected_profile = "GATE_REPLAY"
        commands = {gate_command}
        retained_checks.add(f"gate-replay:{gate_id}")
    else:
        selected_profile = max(minimum_profiles, key=lambda name: _PROFILE_ORDER[name]) if minimum_profiles else "FINAL_HEAD"
        if stage == "FINAL_HEAD":
            selected_profile = "FINAL_HEAD"
        commands.update(registry.profiles[selected_profile].commands)

    logical = {
        "schema": "ovc-test-selection-manifest/v1",
        "registry_id": registry.registry_id,
        "registry_hash": registry.registry_hash,
        "stage": stage,
        "changed_paths": list(paths),
        "selected_profile": selected_profile,
        "status": status,
        "matched_rules": sorted(matched_rows, key=lambda row: (row["path"], row["rule_id"])),
        "unknown_paths": sorted(unknown_paths),
        "ambiguous_paths": sorted(ambiguous_paths),
        "commands": sorted(commands),
        "retained_checks": sorted(retained_checks),
        "blockers": blockers,
        "gate_id": gate_id,
        "final_assurance_required": True,
        "final_assurance_profile": "FINAL_HEAD",
        "gate_replay_substitution": "PROHIBITED",
        "local_success_substitutes_remote_required_check": False,
        "authority": {
            "test_selection": "DETERMINISTIC_ONLY",
            "writes_performed": False,
            "repository_bot_write": "DENIED",
            "direct_main_write": "DENIED",
            "force_push": "DENIED",
            "release": "DENIED",
            "selector": "DENIED",
            "r2": "DENIED",
            "validation": "DENIED",
        },
    }
    return {**logical, "selection_manifest_id": canonical_sha256(logical, role="TEST_SELECTION_MANIFEST")}
