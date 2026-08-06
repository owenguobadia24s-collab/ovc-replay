#!/usr/bin/env python3
"""Validate the MG-WP0 baseline, evidence and authority bindings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1"
WP0 = BASE / "mg-wp0"
D0 = BASE / "mg-d0"
BINDING = WP0 / "MG_WP0_BASELINE_BINDING.json"
INVENTORY = WP0 / "MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json"
EVIDENCE = D0 / "MG_D0_VERIFIED_SHADOW_EVIDENCE_LOCK.json"
SUPERSESSION = D0 / "MG_D0_OPERATOR_SCOPE_AND_C2E_SUPERSESSION.json"
G0_RECEIPT = D0 / "MG_G0_POST_MERGE_RECEIPT.json"
ADMISSION_RECEIPT = (
    ROOT
    / "docs/releases/programme-genesis-native-portfolio-v0-2/"
    "post-snapshot-admissions/MG_POST_SNAPSHOT_ADMISSION_POST_MERGE_RECEIPT.json"
)
IMPLEMENTATION_REGISTRY = (
    ROOT
    / "registries/opt_b/market_grammar/"
    "OVC_MARKET_GRAMMAR_IMPLEMENTATION_REGISTRY_v0_1.jsonc"
)

PROGRAMME_ID = "OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1"
PLAN_ID = "OVC-C2E-C2G-C2P-INTEGRATED-MARKET-GRAMMAR-IMPLEMENTATION"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path.relative_to(ROOT)}")
    return value


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def validate() -> dict[str, Any]:
    binding = load(BINDING)
    inventory = load(INVENTORY)
    evidence = load(EVIDENCE)
    supersession = load(SUPERSESSION)
    g0_receipt = load(G0_RECEIPT)
    admission_receipt = load(ADMISSION_RECEIPT)
    registry = load(IMPLEMENTATION_REGISTRY)

    if binding["programme_id"] != PROGRAMME_ID or binding["plan_id"] != PLAN_ID:
        raise AssertionError("programme or plan identity mismatch")
    if binding["baseline_main"] != "93f56d278d4c35cf2a338a9f3dc7d6ed9e668d69":
        raise AssertionError("MG-WP0 baseline mismatch")

    for artifact in binding["exact_repository_artifacts"]:
        path = ROOT / artifact["path"]
        if not path.is_file():
            raise AssertionError(f"missing repository artifact: {artifact['path']}")
        if artifact["mode"] == "IMMUTABLE_INPUT":
            actual = git_blob_sha1(path.read_bytes())
            if actual != artifact["git_blob_sha1"]:
                raise AssertionError(
                    f"repository artifact identity drift: {artifact['path']}"
                )

    if evidence["status"] != "PASS":
        raise AssertionError("verified shadow evidence lock not PASS")
    if evidence["programme_id"] != PROGRAMME_ID:
        raise AssertionError("evidence programme mismatch")
    replay = evidence["revised_c2_replay"]
    counts = replay["counts"]
    if counts["requested"] != counts["computable"] + counts["censored"] + counts["not_evaluable"]:
        raise AssertionError("replay count reconciliation failed")
    if replay["logical_population_sha256"] != inventory["logical_population_sha256"]:
        raise AssertionError("logical population hash mismatch")
    if replay["binding_sha256"] != inventory["binding"]["binding_sha256"]:
        raise AssertionError("binding hash mismatch")
    if replay["source_objects"] != inventory["external_objects"]:
        raise AssertionError("source-object inventory mismatch")
    if replay["run_manifests"] != inventory["run_manifests"]:
        raise AssertionError("run-manifest inventory mismatch")

    if g0_receipt["status"] != "COMPLETED" or not g0_receipt["effective"]:
        raise AssertionError("MG-G0 receipt not effective")
    if g0_receipt["merge_commit"] != "114558efdf38f56499f6276da917190c3cb729ea":
        raise AssertionError("MG-G0 merge mismatch")
    if admission_receipt["programme_id"] != PROGRAMME_ID or not admission_receipt["effective"]:
        raise AssertionError("post-snapshot admission not effective")
    if admission_receipt["reserved_authority"] != "NONE":
        raise AssertionError("unexpected reserved authority in admission")

    if supersession["authority_effect"] != "LIMITED_IMMUTABLE_SUPERSESSION":
        raise AssertionError("C2E supersession scope mismatch")
    required_denials = {"C2E_ACTIVATION", "C2E_AUTHORITATIVE_CONSUMPTION"}
    if not required_denials.issubset(set(supersession["preserved_denials"])):
        raise AssertionError("C2E activation denials not preserved")

    if registry["programme_id"] != PROGRAMME_ID or registry["status"] != "APPROVED_FOR_BOUNDED_SHADOW_BUILD":
        raise AssertionError("implementation registry not approved for bounded shadow build")
    if any(component["authority"] != "SHADOW_EXPERIMENT" for component in registry["components"]):
        raise AssertionError("non-shadow component authority detected")
    forbidden = set(registry["forbidden_dependencies"])
    required_forbidden = {
        "C2E_READS_C2G",
        "C2G_REWRITES_C2_OR_C2E",
        "C2P_MUTATES_GRAMMAR",
        "OUTCOME_INPUT_TO_C2E_C2G_C2P_CONSTRUCTION",
        "PROVENANCE_AS_STRUCTURAL_MATCH_FEATURE",
    }
    if not required_forbidden.issubset(forbidden):
        raise AssertionError("required forbidden dependency missing")

    return {
        "baseline_main": binding["baseline_main"],
        "repository_artifact_count": len(binding["exact_repository_artifacts"]),
        "external_object_count": len(inventory["external_objects"]),
        "requested": counts["requested"],
        "logical_population_sha256": replay["logical_population_sha256"],
        "integrated_package_sha256": inventory["integrated_package"]["package_sha256"],
        "authority": binding["authority"],
        "status": "PASS",
    }


def main() -> int:
    print("MG_WP0_VALIDATION=" + json.dumps(validate(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
