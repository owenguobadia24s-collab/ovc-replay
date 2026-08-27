#!/usr/bin/env python3
"""Conflict-free reference review for the DIASI-WP1 deterministic substrate."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import (
    DiasContractError,
    OwnerFactCandidate,
    OwnerFactConflict,
    classify_consequence,
    resolve_owner_fact,
)


REFERENCE_PLANES = {
    "FLOW": {"SCHEDULE", "ROUTE", "RETRY", "PLACEMENT", "LEASE", "RECONCILE", "EVENT_CURSOR", "RELEASE_SUCCESSOR"},
    "EVIDENCE": {"PRODUCE_EVIDENCE", "CONSUME_EVIDENCE", "VALIDATE", "QUALIFY", "PUBLISH_EVIDENCE", "CHANGE_SOURCE_CONSUMER_ROLE", "CHANGE_PROTECTED_POPULATION", "CHANGE_RESEARCH_ROLE"},
    "AUTHORITY": {"GRANT", "REVOKE", "CUTOVER", "FREEZE_INTAKE", "TRANSFER_WRITER", "RETIRE", "REMOVE", "PROOF_SUBSTITUTE", "ASSURANCE_COMPRESS", "LIVE_WRITE", "EXPOSURE", "MARKET_EXECUTION", "CHANGE_RULESET", "CHANGE_OWNER"},
}
REFERENCE_ORDER = ("FLOW", "EVIDENCE", "AUTHORITY")
REFERENCE_PRECEDENCE = ("OWNER_CURRENT_POINTER", "OWNER_REFERENCED_STATE", "OWNER_SIGNED_RECEIPT", "DERIVED_OBSERVATION")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def reference_classify(action: Mapping[str, Any]) -> dict[str, Any]:
    effects = action.get("effects")
    if not isinstance(effects, Sequence) or isinstance(effects, (str, bytes)) or not effects:
        raise ValueError("invalid effects")
    if len(effects) != len(set(effects)):
        raise ValueError("duplicate effects")
    known = set().union(*REFERENCE_PLANES.values())
    if set(effects) - known:
        raise ValueError("unknown effects")
    planes = {plane for plane, members in REFERENCE_PLANES.items() if set(effects) & members}
    if action.get("source_consumer_role_change") is True:
        planes.add("EVIDENCE")
    if action.get("authority_delta") not in (None, "", "NONE"):
        planes.add("AUTHORITY")
    ordered = [plane for plane in REFERENCE_ORDER if plane in planes]
    return {
        "planes": ordered,
        "controlling_plane": ordered[-1],
        "requires_split": "AUTHORITY" in planes and len(planes) > 1,
    }


def review_classifier(corpus: Mapping[str, Any]) -> dict[str, Any]:
    comparisons = 0
    permutations = 0
    for case in corpus["cases"]:
        expected = reference_classify(case["action"])
        observed = classify_consequence(case["action"])
        actual = {
            "planes": list(observed.planes),
            "controlling_plane": observed.controlling_plane,
            "requires_split": observed.requires_split,
        }
        if actual != expected or actual != case["expected"]:
            raise AssertionError(f"classifier divergence: {case['id']}")
        comparisons += 1
        for permutation in itertools.permutations(case["action"]["effects"]):
            variant = {**case["action"], "effects": list(permutation)}
            variant_observed = classify_consequence(variant)
            if list(variant_observed.planes) != expected["planes"] or variant_observed.controlling_plane != expected["controlling_plane"]:
                raise AssertionError(f"permutation divergence: {case['id']}")
            permutations += 1
    for case in corpus["negative_cases"]:
        try:
            classify_consequence(case["action"])
        except DiasContractError:
            comparisons += 1
        else:
            raise AssertionError(f"negative case survived: {case['id']}")

    dominance_checks = 0
    for authority_effect in sorted(REFERENCE_PLANES["AUTHORITY"]):
        for companion in ("ROUTE", "PRODUCE_EVIDENCE"):
            observed = classify_consequence({"action_id": "dominance", "effects": [authority_effect, companion]})
            if observed.controlling_plane != "AUTHORITY" or not observed.requires_split:
                raise AssertionError(f"authority dominance failed: {authority_effect}+{companion}")
            dominance_checks += 1
    return {"corpus_comparisons": comparisons, "permutation_checks": permutations, "authority_dominance_checks": dominance_checks}


def review_owner_precedence() -> dict[str, Any]:
    candidates = []
    for index, source_class in enumerate(REFERENCE_PRECEDENCE):
        candidates.append(
            OwnerFactCandidate(
                owner="OWNER",
                fact_key="fact",
                value=source_class,
                source_class=source_class,
                source_path=f"records/{index}.json",
                source_blob=f"{index + 1:040x}",
                observed_at=f"2099-01-0{index + 1}T00:00:00Z",
            )
        )
    resolved = resolve_owner_fact(candidates)
    if resolved.value != REFERENCE_PRECEDENCE[0]:
        raise AssertionError("recency or input order overrode owner precedence")

    left = OwnerFactCandidate("OWNER", "fact", "A", "OWNER_CURRENT_POINTER", "records/a.json", "a" * 40)
    right = OwnerFactCandidate("OWNER", "fact", "B", "OWNER_CURRENT_POINTER", "records/b.json", "b" * 40)
    try:
        resolve_owner_fact([left, right])
    except OwnerFactConflict:
        pass
    else:
        raise AssertionError("equal-tier conflict did not block")
    return {"precedence_order": list(REFERENCE_PRECEDENCE), "recency_override_rejected": True, "equal_tier_conflict_blocked": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--subject-head", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    subject_head = _git(repo, "rev-parse", f"{args.subject_head}^{{commit}}")
    subject_tree = _git(repo, "rev-parse", f"{subject_head}^{{tree}}")
    corpus_path = repo / "fixtures/development_skills/dias/DIASI_WP1_ADVERSARIAL_CLASSIFIER_CORPUS_v0_1.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    result = {
        "schema": "ovc-diasi-algorithmic-review/v1",
        "review_id": "PENDING",
        "reviewer_identity": "DIASI_CONFLICT_FREE_REFERENCE_ORACLE_v0_1",
        "reviewer_role": "ALGORITHMIC_ORACLE_NO_AUTHORITY_NO_WRITE",
        "independence": "SEPARATE_CLOSED_DECISION_TABLE_AND_PROPERTY_ORACLE_FRESH_PROCESS",
        "external_human_or_model_claim": False,
        "subject_head": subject_head,
        "subject_tree": subject_tree,
        "corpus_id": corpus["corpus_id"],
        "classifier": review_classifier(corpus),
        "owner_precedence": review_owner_precedence(),
        "decision": "PASS",
        "blockers": [],
        "authority_effect": "NONE",
    }
    result["review_id"] = canonical_sha256({key: value for key, value in result.items() if key != "review_id"})
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
