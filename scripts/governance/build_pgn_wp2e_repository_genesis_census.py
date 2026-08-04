#!/usr/bin/env python3
"""Build the PGN-WP2E repository-genesis census from repository evidence only."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "registries/governance/programme_genesis/PGN_REPOSITORY_GENESIS_CLASSIFICATION_POLICY_v0_1.json"
OUTPUT_PATH = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"

ID_KEYS = {"programme_id", "program_id", "proposed_programme_id", "plan_id", "release_id"}
TEXT_PATTERNS = {
    "programme_id": re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:programme(?:\s+id)?|program(?:\s+id)?)\s*[:=]\s*[`\"']?([^`\"'\n]+)"),
    "plan_id": re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:plan(?:\s+id)?)\s*[:=]\s*[`\"']?([^`\"'\n]+)"),
    "release_id": re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:release(?:\s+id)?)\s*[:=]\s*[`\"']?([^`\"'\n]+)"),
}
VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/\-]{2,159}$")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".txt", ".csv"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path.relative_to(ROOT)}")
    return value


def clean_id(value: str) -> str | None:
    value = value.strip().strip("`\"'[](){}.,; ")
    value = value.split("  ", 1)[0].strip()
    if " " in value or not VALID_ID.fullmatch(value):
        return None
    return value


def walk_json(value: Any, path: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ID_KEYS and isinstance(item, str):
                object_id = clean_id(item)
                if object_id:
                    found.append((key, object_id))
            found.extend(walk_json(item, path + (str(key),)))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk_json(item, path))
    return found


def source_role(key: str) -> str:
    if key in {"programme_id", "program_id", "proposed_programme_id"}:
        return "PROGRAMME_IDENTITY"
    if key == "plan_id":
        return "IMPLEMENTATION_PLAN_IDENTITY"
    if key == "release_id":
        return "RELEASE_IDENTITY"
    return "DISCOVERED_IDENTITY"


def discover_sources(policy: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    identities: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scanned: list[dict[str, Any]] = []
    for root_name in policy["discovery_roots"]:
        root = ROOT / root_name
        if not root.exists():
            scanned.append({"root": root_name, "status": "MISSING"})
            continue
        file_count = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel == OUTPUT_PATH.relative_to(ROOT).as_posix() or any(part in SKIP_PARTS for part in path.parts):
                continue
            data = path.read_bytes()
            file_count += 1
            source = {"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)}
            pairs: set[tuple[str, str]] = set()
            if path.suffix.lower() == ".json":
                try:
                    pairs.update(walk_json(json.loads(data.decode("utf-8"))))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            for key, pattern in TEXT_PATTERNS.items():
                for match in pattern.finditer(text):
                    object_id = clean_id(match.group(1))
                    if object_id:
                        pairs.add((key, object_id))
            for key, object_id in sorted(pairs):
                identities[object_id].append({**source, "identity_key": key, "role": source_role(key)})
        scanned.append({"root": root_name, "status": "PRESENT", "file_count": file_count})
    return identities, scanned


def release_initiatives(policy: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prefix in policy["bounded_release_prefixes"]:
        root = ROOT / prefix
        if not root.exists():
            continue
        for child in sorted(p for p in root.iterdir() if p.is_dir()):
            files = sorted(p for p in child.rglob("*") if p.is_file())
            if not files:
                continue
            digest = hashlib.sha256()
            total = 0
            for path in files:
                rel = path.relative_to(ROOT).as_posix().encode("utf-8")
                data = path.read_bytes()
                digest.update(len(rel).to_bytes(4, "big")); digest.update(rel)
                digest.update(len(data).to_bytes(8, "big")); digest.update(data)
                total += len(data)
            object_id = "INITIATIVE::" + child.relative_to(ROOT).as_posix()
            items[object_id].append({
                "path": child.relative_to(ROOT).as_posix(),
                "sha256": digest.hexdigest(),
                "bytes": total,
                "identity_key": "release_root",
                "role": "MAJOR_BOUNDED_INITIATIVE_ROOT",
                "member_count": len(files),
            })
    return items


def plane_of(sources: list[dict[str, Any]]) -> str:
    paths = [item["path"] for item in sources]
    historical = [p for p in paths if p.startswith("legacy/quarantine/") or p.startswith("docs/history/")]
    current = [p for p in paths if p not in historical]
    if current and historical:
        return "CURRENT_AND_HISTORICAL"
    if current:
        return "CURRENT"
    return "HISTORICAL"


def classify(object_id: str, sources: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[str, str, list[str], str]:
    explicit = policy["explicit_classifications"].get(object_id)
    if explicit:
        return explicit["classification"], explicit["object_kind"], list(explicit.get("successors", [])), "EXPLICIT_POLICY"
    if object_id.startswith("INITIATIVE::"):
        return "BOUNDED_PACKET_NOT_A_PROGRAMME", "MAJOR_BOUNDED_INITIATIVE", [], "RELEASE_ROOT"
    roles = {item["role"] for item in sources}
    paths = [item["path"] for item in sources]
    current_programme = any(item["role"] == "PROGRAMME_IDENTITY" and not item["path"].startswith(("legacy/quarantine/", "docs/history/")) for item in sources)
    historical_only = plane_of(sources) == "HISTORICAL"
    joined = "\n".join(path.lower() for path in paths)
    if object_id in policy["native_programmes"]:
        return "NATIVE_PROGRAMME", "FORMAL_PROGRAMME", [], "EXPLICIT_NATIVE"
    if object_id in policy["proposal_not_admitted"] or "not_admitted" in joined or "preparation_state" in joined:
        return "PROPOSAL_NOT_ADMITTED", "NON_ADMITTED_PROPOSAL", [], "ADMISSION_EVIDENCE"
    if roles == {"IMPLEMENTATION_PLAN_IDENTITY"}:
        return "BOUNDED_PACKET_NOT_A_PROGRAMME", "IMPLEMENTATION_PLAN", [], "PLAN_ID_ONLY"
    if roles == {"RELEASE_IDENTITY"}:
        if historical_only:
            return "UNRESOLVED", "HISTORICAL_RELEASE", [], "HISTORICAL_RELEASE_WITHOUT_EXPLICIT_LINEAGE"
        return "BOUNDED_PACKET_NOT_A_PROGRAMME", "HISTORICAL_RELEASE", [], "RELEASE_ID_ONLY"
    if current_programme:
        return "LEGACY_PROGRAMME_REQUIRING_CONVERSION", "FORMAL_PROGRAMME", [], "CURRENT_NON_NATIVE_PROGRAMME_STATE"
    if historical_only and "supersed" in joined:
        return "SUPERSEDED_PROGRAMME", "SUPERSEDED_PROGRAMME_VERSION", [], "HISTORICAL_SUPERSESSION_PATH"
    if historical_only:
        return "UNRESOLVED", "SUPERSEDED_PROGRAMME_VERSION", [], "HISTORICAL_IDENTITY_WITHOUT_ACCEPTED_LINEAGE"
    if "PROGRAMME_IDENTITY" in roles:
        return "LEGACY_PROGRAMME_REQUIRING_CONVERSION", "IMPLEMENTATION_PROGRAMME", [], "CURRENT_PROGRAMME_EVIDENCE"
    return "UNRESOLVED", "MAJOR_BOUNDED_INITIATIVE", [], "NO_SAFE_CLASSIFICATION"


def build_census(root: Path = ROOT) -> dict[str, Any]:
    if root != ROOT:
        raise AssertionError("alternate roots are not supported because source identities are repository-relative")
    policy = read_json(POLICY_PATH)
    identities, scanned_roots = discover_sources(policy)
    for object_id, sources in release_initiatives(policy).items():
        identities[object_id].extend(sources)
    for object_id, override in policy["explicit_classifications"].items():
        if object_id not in identities:
            evidence = ROOT / override["evidence"]
            data = evidence.read_bytes()
            identities[object_id].append({
                "path": override["evidence"], "sha256": sha256_bytes(data), "bytes": len(data),
                "identity_key": "explicit_policy", "role": "EXPLICIT_CLASSIFICATION_EVIDENCE",
            })
    objects: list[dict[str, Any]] = []
    for object_id in sorted(identities):
        sources = sorted({json.dumps(item, sort_keys=True): item for item in identities[object_id]}.values(), key=lambda item: (item["path"], item["role"]))
        classification, object_kind, successors, rationale = classify(object_id, sources, policy)
        objects.append({
            "object_id": object_id,
            "object_kind": object_kind,
            "classification": classification,
            "classification_rationale": rationale,
            "evidence_plane": plane_of(sources),
            "sources": sources,
            "successors": successors,
            "candidate_constructed": False,
            "authority_effect": "NONE",
        })
    classification_counts = dict(sorted(Counter(item["classification"] for item in objects).items()))
    kind_counts = dict(sorted(Counter(item["object_kind"] for item in objects).items()))
    unresolved = [item["object_id"] for item in objects if item["classification"] == "UNRESOLVED"]
    exclusions = [
        {"object_id": item["object_id"], "classification": item["classification"], "reason": item["classification_rationale"]}
        for item in objects if item["classification"] in {"BOUNDED_PACKET_NOT_A_PROGRAMME", "PROPOSAL_NOT_ADMITTED", "SUPERSEDED_PROGRAMME", "ABSORBED_INTO_SUCCESSOR"}
    ]
    lineage = [
        {"object_id": item["object_id"], "classification": item["classification"], "successors": item["successors"], "evidence": item["sources"]}
        for item in objects if item["successors"] or item["classification"] in {"SUPERSEDED_PROGRAMME", "ABSORBED_INTO_SUCCESSOR"}
    ]
    result: dict[str, Any] = {
        "schema": "ovc-pgn-repository-genesis-census/v2",
        "programme_id": policy["programme_id"],
        "plan_id": policy["plan_id"],
        "packet_id": "PGN-WP2E",
        "gate_id": "PGN-G2B",
        "baseline_main": policy["baseline_main"],
        "policy_path": POLICY_PATH.relative_to(ROOT).as_posix(),
        "policy_sha256": sha256_bytes(POLICY_PATH.read_bytes()),
        "coverage": {
            "requested_start": "INITIAL_OVC_REPLAY_COMMIT",
            "earliest_reproducible_snapshot": policy["earliest_reproducible_repository_snapshot"],
            "initial_commit_resolved": False,
            "pre_snapshot_history": "UNRESOLVED",
            "scanned_roots": scanned_roots,
        },
        "classification_enum": policy["classification_enum"],
        "object_count": len(objects),
        "classification_counts": classification_counts,
        "object_kind_counts": kind_counts,
        "objects": objects,
        "exclusion_ledger": exclusions,
        "lineage_consolidation_ledger": lineage,
        "coverage_and_unresolved_ledger": {
            "unresolved_count": len(unresolved),
            "unresolved_object_ids": unresolved,
            "initial_commit_gap_object": "COVERAGE::PRE_C0AD7BA_GIT_HISTORY",
        },
        "authority": {
            "candidate_construction": "DENIED_PENDING_PGN_G2B",
            "native_adoption": "DENIED_PENDING_PGN_G3_AFTER_PGN_G2B",
            "authority_effect": "NONE",
        },
        "next_action": "OPERATOR_ACKNOWLEDGE_EXPANDED_CENSUS_EXCLUSIONS_AND_LINEAGE_AT_PGN_G2B",
        "rollback": policy["rollback"],
    }
    digest_body = dict(result)
    result["census_sha256"] = sha256_bytes(canonical(digest_body))
    return result


def main() -> int:
    value = build_census()
    print("PGN_WP2E_CENSUS=" + json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
