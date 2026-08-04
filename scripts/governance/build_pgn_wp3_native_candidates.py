from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/governance/programme_genesis/PGN_WP3_CLASS_REGISTRY_v0_1.json"
CANDIDATE_DIR = ROOT / "registries/governance/programme_genesis/pgn_candidates"
MANIFEST = CANDIDATE_DIR / "PGN_WP3_NATIVE_CANDIDATE_PORTFOLIO_v0_1.json"
QUEUE = CANDIDATE_DIR / "PGN_WP3_PROGRESSIVE_REVIEW_QUEUE_v0_1.json"
REVIEW_RECEIPT_DIR = (
    ROOT
    / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews"
)

UNRESOLVED_FIELDS = [
    "PURPOSE_EXACT_SOURCE_TEXT",
    "INCLUDED_SCOPE_EXACT_SOURCE_TEXT",
    "EXCLUDED_SCOPE_EXACT_SOURCE_TEXT",
    "CONSTITUTIONAL_PARENT",
    "PROGRAMME_PARENTS",
    "CREATION_TRIGGERS",
    "AUTHORITY_ENVELOPE_FIELD_LEVEL_CROSSWALK",
    "LIFECYCLE_EXIT_CRITERIA",
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def build_candidate(entry: dict[str, Any]) -> dict[str, Any]:
    source = entry["census_source"]
    dossier = entry["historical_source_dossier"]
    return {
        "object_type": "NATIVE_CANDIDATE",
        "authority_effect": "NONE",
        "native_candidate": {
            "programme_id": entry["programme_id"],
            "candidate_class": entry["candidate_class"],
            "status": "CANDIDATE_UNAPPROVED",
            "sources": [source],
            "authority_envelope": {
                "source_authority_preserved": True,
                "authority_delta": "NONE",
                "native_adoption": "DENIED_PENDING_PGN_G3",
                "reserved_authority": "NONE",
            },
            "scope_audit": {
                "profile": "RETROSPECTIVE_SOURCE_PRESERVING",
                "purpose": "UNRESOLVED_EXACT_SOURCE_TEXT",
                "included_scope": "UNRESOLVED_EXACT_SOURCE_TEXT",
                "excluded_scope": "UNRESOLVED_EXACT_SOURCE_TEXT",
                "current_authority_vs_candidate": "PRESERVED_NO_DELTA",
                "fabricated_historical_intent": False,
            },
            "migration_crosswalk": {
                "acknowledged_classification": "LEGACY_PROGRAMME_REQUIRING_CONVERSION",
                "primary_source_path": dossier["primary_source_path"],
                "source_count": dossier["source_count"],
                "source_set_sha256": dossier["source_set_sha256"],
                "identity_preserved": True,
                "source_values_modified": False,
                "review_domain": entry["review_domain"],
            },
            "unresolved_fields": UNRESOLVED_FIELDS,
            "lifecycle": {
                "projection_status": "PRESERVED_BY_SOURCE_REFERENCE_UNAPPROVED",
                "source_lifecycle_modified": False,
                "native_lifecycle_effect": "NONE_PENDING_PGN_G3",
            },
        },
    }


def grouped_entries(
    entries: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for entry in entries:
        domain = entry["review_domain"]
        if not groups or groups[-1][0] != domain:
            groups.append((domain, []))
        groups[-1][1].append(entry)
    if len(groups) != 6:
        raise ValueError(f"expected six progressive review groups, got {len(groups)}")
    for domain, members in groups:
        if not 1 <= len(members) <= 3:
            raise ValueError(f"review group {domain} has {len(members)} members")
    return groups


def build_bundle(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = load_json(root / REGISTRY.relative_to(ROOT))
    entries = registry["entries"]
    if len(entries) != 16:
        raise ValueError("PGN-WP3 requires exactly sixteen acknowledged candidates")

    candidates = [build_candidate(entry) for entry in entries]
    candidate_set_sha = sha256(candidates)
    commitments = [
        {
            "programme_id": candidate["native_candidate"]["programme_id"],
            "candidate_class": candidate["native_candidate"]["candidate_class"],
            "candidate_sha256": sha256(candidate),
            "status": "CANDIDATE_UNAPPROVED",
            "authority_effect": "NONE",
        }
        for candidate in candidates
    ]
    manifest = {
        "schema": "ovc-pgn-wp3-native-candidate-commitment-portfolio/v1",
        "programme_id": "OVC-PG-NATIVE-PORTFOLIO-v0.2",
        "plan_id": "OVC-PGN-IMPLEMENTATION-PLAN-0.2-REVISED",
        "plan_version": "0.2",
        "packet_id": "PGN-WP3",
        "baseline_commit": "38de6b53a692d2f9f71c506b833bf6ffb92820f6",
        "operator_prerequisite": "PGN-G2B.OPERATOR.ACKNOWLEDGE_CONTINUE.20260804T132000+0100",
        "status": "SEALED_CANDIDATE_COMMITMENTS_UNAPPROVED",
        "authority_effect": "NONE",
        "candidate_count": 16,
        "candidate_set_sha256": candidate_set_sha,
        "commitment_set_sha256": sha256(commitments),
        "census_bundle_sha256": "b3fe76028609c7ab45b0779411df8206f0aaf22eecaaf6ff20f4106f49387b68",
        "candidate_commitments": commitments,
        "materialization": {
            "current_disclosed_group": "PGN-G3-R1",
            "current_group_materialization": "AUTHORISED_AFTER_PGN_WP3_MERGE",
            "future_group_materialization": "DENIED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT_RECEIPT",
            "builder": "scripts/governance/build_pgn_wp3_native_candidates.py",
        },
        "authority": {
            "native_adoption": "DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3",
            "cross_programme_edge_adoption": "DENIED_PENDING_PGN_G5",
            "migration_warning_closure": "DENIED_PENDING_PGN_G6",
            "reserved_authority": "NONE",
        },
        "rollback": "Discard and rebuild sealed candidate commitments from the acknowledged census. No source record or programme authority is modified.",
    }

    groups = grouped_entries(entries)
    queue_groups: list[dict[str, Any]] = []
    for index, (domain, members) in enumerate(groups, start=1):
        group_id = f"PGN-G3-R{index}"
        candidate_ids = [entry["programme_id"] for entry in members]
        visible = index == 1
        queue_groups.append(
            {
                "group_id": group_id,
                "sequence": index,
                "grouping_basis": "AUTHORITY_DOMAIN",
                "review_domain": domain,
                "candidate_count": len(candidate_ids),
                "candidate_ids": candidate_ids if visible else [],
                "sealed_candidate_ids_sha256": sha256(candidate_ids),
                "sealed_candidate_bodies_sha256": sha256(
                    [build_candidate(entry) for entry in members]
                ),
                "disclosure_status": (
                    "DISCLOSED_PENDING_OPERATOR_ACKNOWLEDGEMENT"
                    if visible
                    else "LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT"
                ),
                "acknowledgement_required": True,
                "adoption_effect": "NONE",
                "unlock_condition": (
                    None
                    if visible
                    else f"PGN-G3-R{index - 1}_ACKNOWLEDGEMENT_RECEIPT_MERGED"
                ),
            }
        )
    queue = {
        "schema": "ovc-pgn-wp3-progressive-review-queue/v1",
        "programme_id": "OVC-PG-NATIVE-PORTFOLIO-v0.2",
        "plan_id": "OVC-PGN-IMPLEMENTATION-PLAN-0.2-REVISED",
        "plan_version": "0.2",
        "packet_id": "PGN-WP3",
        "baseline_commit": "38de6b53a692d2f9f71c506b833bf6ffb92820f6",
        "status": "PGN_G3_R1_DISCLOSED_REMAINING_GROUPS_LOCKED",
        "authority_effect": "NONE",
        "maximum_candidates_per_group": 3,
        "group_count": len(queue_groups),
        "candidate_count": len(candidates),
        "candidate_set_sha256": candidate_set_sha,
        "groups": queue_groups,
        "rules": {
            "current_group": "PGN-G3-R1",
            "next_group_disclosure_before_acknowledgement": "DENIED",
            "group_acknowledgement_is_adoption": False,
            "per_programme_adoption_gate": "PGN-G3",
            "future_group_member_ids_disclosed": False,
        },
        "rollback": "Keep all later groups locked and rebuild the queue from the exact sealed candidate commitments.",
    }
    return manifest, queue


def _required_receipt(group_number: int, root: Path) -> Path | None:
    if group_number == 1:
        return None
    return (
        root
        / REVIEW_RECEIPT_DIR.relative_to(ROOT)
        / f"PGN_G3_R{group_number - 1}_ACKNOWLEDGEMENT_RECEIPT.json"
    )


def build_group(
    group_id: str, root: Path = ROOT
) -> dict[str, Any]:
    if not group_id.startswith("PGN-G3-R"):
        raise ValueError(f"invalid group id: {group_id}")
    try:
        group_number = int(group_id.rsplit("R", 1)[1])
    except ValueError as exc:
        raise ValueError(f"invalid group id: {group_id}") from exc
    registry = load_json(root / REGISTRY.relative_to(ROOT))
    groups = grouped_entries(registry["entries"])
    if not 1 <= group_number <= len(groups):
        raise ValueError(f"unknown group: {group_id}")
    required_receipt = _required_receipt(group_number, root)
    if required_receipt is not None and not required_receipt.exists():
        raise PermissionError(
            f"{group_id} remains locked until {required_receipt.name} exists"
        )
    domain, members = groups[group_number - 1]
    candidates = [build_candidate(entry) for entry in members]
    return {
        "schema": "ovc-pgn-wp3-native-candidate-group/v1",
        "programme_id": "OVC-PG-NATIVE-PORTFOLIO-v0.2",
        "plan_id": "OVC-PGN-IMPLEMENTATION-PLAN-0.2-REVISED",
        "plan_version": "0.2",
        "packet_id": "PGN-WP3",
        "review_group_id": group_id,
        "review_domain": domain,
        "status": "CANDIDATE_GROUP_UNAPPROVED",
        "authority_effect": "NONE",
        "candidate_count": len(candidates),
        "candidate_ids": [entry["programme_id"] for entry in members],
        "candidate_group_sha256": sha256(candidates),
        "candidates": candidates,
        "native_adoption": "DENIED_PENDING_PGN_G3",
    }


def materialize(root: Path = ROOT) -> None:
    manifest, queue = build_bundle(root)
    candidate_dir = root / CANDIDATE_DIR.relative_to(ROOT)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (root / MANIFEST.relative_to(ROOT)).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / QUEUE.relative_to(ROOT)).write_text(
        json.dumps(queue, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    manifest, queue = build_bundle()
    print(
        json.dumps(
            {
                "candidate_count": manifest["candidate_count"],
                "candidate_set_sha256": manifest["candidate_set_sha256"],
                "commitment_set_sha256": manifest["commitment_set_sha256"],
                "manifest_sha256": sha256(manifest),
                "review_queue_sha256": sha256(queue),
                "group_count": queue["group_count"],
                "current_group": queue["rules"]["current_group"],
                "authority_effect": manifest["authority_effect"],
            },
            sort_keys=True,
        )
    )
