from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .gen0002 import audit_frozen_passport_subject_identity

SOURCE_CENSUS_DIR = Path("docs/programmes/lsiac-v0-1/source-census")
PASSPORT_SUMMARY = SOURCE_CENSUS_DIR / "LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"
POST_DELTA = SOURCE_CENSUS_DIR / "LSIAC_POST_V0_5_DELTA_MANIFEST_v0_1.json"

EXPECTED_SUBJECT_COUNT = 431
EXPECTED_PASSPORT_COUNT = 434
EXPECTED_SOURCE_PASSPORT_SET_SHA256 = "f97ba927944326864f1a5cc20ecc69a0a4623743231aa8479d713984bbe68019"
EXPECTED_POST_DELTA_SHA256 = "1ed67410854478b2947d62055b3b619ad8081c782907c66efa78bbf1d823a42d"
GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
PROTOCOL_ID = "OVC-LSIAC-ACCESSION-ADJUDICATION-PROTOCOL-0.1"

STANDING_WEAKNESS = {
    "PENDING_SOURCE_BINDING": 0,
    "SOURCE_DERIVED": 1,
    "SOURCE_BOUND_EXTERNAL": 2,
    "SOURCE_EXACT": 3,
}
AVAILABILITY_WEAKNESS = {
    "MISSING": 0,
    "VERIFIED_ONCE_UNBOUND": 1,
    "PRESENT_RETRIEVABLE": 2,
}
REPRODUCIBILITY_WEAKNESS = {
    "SYNTHESIS_ONLY": 0,
    "RESULT_ONLY": 1,
    "ORIGINAL_SOURCE_EXACT": 2,
}
ALLOWED_DISPOSITIONS = {
    "SUPPORTED_SCOPED", "NEGATIVE_SUPPORTED", "PARTIAL",
    "REPRESENTATION_DEPENDENT", "METHOD_DEPENDENT",
    "TEMPORALLY_HETEROGENEOUS", "UNRESOLVED", "NOT_EVALUABLE",
}
ALLOWED_EXPOSURE = {
    "FRESH_UNTOUCHED", "DISCOVERY_EXPOSED", "DEVELOPMENT_EXPOSED",
    "POST_HOC", "CONTAMINATED", "UNKNOWN",
}


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected object: {path}")
    return value


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _invert(codebook: Mapping[str, int]) -> dict[int, str]:
    return {int(value): str(key) for key, value in codebook.items()}


def load_source_passports(root: str | Path) -> list[dict[str, Any]]:
    """Decode the frozen source passports after GEN0002 exact-accounting proof."""
    root = Path(root)
    audit = audit_frozen_passport_subject_identity(root)
    if audit["passport_count"] != EXPECTED_PASSPORT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_COUNT_MISMATCH")
    if audit["subject_count"] != EXPECTED_SUBJECT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_SUBJECT_COUNT_MISMATCH")
    if audit["frozen_source_passport_set_sha256"] != EXPECTED_SOURCE_PASSPORT_SET_SHA256:
        raise ValueError("LSIAC_GEN0002_PASS1_SOURCE_PASSPORT_SET_IDENTITY_MISMATCH")

    summary = _load_json(root / PASSPORT_SUMMARY)
    codebooks = summary["codebooks"]
    inverses = {
        name: _invert(mapping)
        for name, mapping in codebooks.items()
        if isinstance(mapping, Mapping)
    }
    field_order = list(summary["field_order"])
    defaults = dict(summary["defaults"])

    passports: list[dict[str, Any]] = []
    for chunk_meta in summary["chunks"]:
        chunk = _load_json(root / SOURCE_CENSUS_DIR / str(chunk_meta["file"]))
        rows = chunk.get("rows")
        if not isinstance(rows, list) or len(rows) != int(chunk_meta["count"]):
            raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_CHUNK_COUNT_MISMATCH")
        if chunk.get("h") != chunk_meta.get("canonical_sha256"):
            raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_CHUNK_CANONICAL_ID_MISMATCH")
        for row in rows:
            if not isinstance(row, list) or len(row) < 9:
                raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_ROW_INVALID")
            raw = dict(zip(field_order, list(row) + [None] * max(0, len(field_order) - len(row))))
            decoded = dict(defaults)
            decoded.update({
                "passport_id": str(raw["id_suffix"]),
                "subject_id": str(raw["subject_ref"]),
                "source_standing": inverses["standing"][int(raw["standing"])],
                "artifact_availability": inverses["availability"][int(raw["availability"])],
                "locator_kind": inverses["locator_kind"][int(raw["locator_kind"])],
                "locator_value": raw["locator_value"],
                "retention": inverses["retention"][int(raw["retention"])],
                "reproducibility_class": inverses["reproducibility"][int(raw["reproducibility"])],
                "source_relation_state": inverses["relation"][int(raw["relation"])],
            })
            extras = raw.get("extras")
            if isinstance(extras, Mapping):
                for key, value in extras.items():
                    if key in {"authority", "exposure"} and isinstance(value, int):
                        decoded[key] = inverses[key][value]
                    else:
                        decoded[key] = value
            passports.append(decoded)
    if len(passports) != EXPECTED_PASSPORT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_RECONSTRUCTED_PASSPORT_COUNT_MISMATCH")
    return passports


def _post_delta_by_subject(root: Path) -> dict[str, Mapping[str, Any]]:
    delta = _load_json(root / POST_DELTA)
    if delta.get("canonical_manifest_sha256") != EXPECTED_POST_DELTA_SHA256:
        raise ValueError("LSIAC_GEN0002_PASS1_POST_DELTA_IDENTITY_MISMATCH")
    entries = delta.get("entries")
    if not isinstance(entries, list):
        raise ValueError("LSIAC_GEN0002_PASS1_POST_DELTA_ENTRIES_INVALID")
    return {str(entry["subject_id"]): entry for entry in entries if isinstance(entry, Mapping)}


def _weakest(values: Iterable[str], order: Mapping[str, int], label: str) -> str:
    values = list(values)
    if not values or (set(values) - set(order)):
        raise ValueError(f"LSIAC_GEN0002_PASS1_{label}_INVALID")
    return min(values, key=lambda value: order[value])


def _normalize_locator(value: object) -> str | None:
    if value is None:
        return None
    token = " ".join(str(value).split()).strip()
    return token or None


def _dependence_groups(passports: list[Mapping[str, Any]]) -> dict[str, list[str]]:
    locator_subjects: dict[str, set[str]] = defaultdict(set)
    for passport in passports:
        locator = _normalize_locator(passport.get("locator_value"))
        if locator and passport.get("locator_kind") != "None":
            locator_subjects[locator].add(str(passport["subject_id"]))
    groups: dict[str, list[str]] = {}
    for locator, subjects in sorted(locator_subjects.items()):
        ordered = sorted(subjects)
        if len(ordered) >= 2:
            group_id = "DEP-LOC-" + hashlib.sha256(locator.encode("utf-8")).hexdigest()[:20]
            groups[group_id] = ordered
    return groups


def build_shared_locator_dependence_graph(passports: list[Mapping[str, Any]]) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    for group_id, subjects in sorted(_dependence_groups(passports).items()):
        for index, left in enumerate(subjects):
            for right in subjects[index + 1:]:
                edge_id = "EDGE-" + hashlib.sha256(f"{group_id}|{left}|{right}".encode("utf-8")).hexdigest()[:24]
                edges.append({
                    "edge_id": edge_id,
                    "left_subject_id": left,
                    "right_subject_id": right,
                    "dependence_class": "SHARED_SOURCE_DEPENDENT",
                    "basis": f"IDENTICAL_FROZEN_SOURCE_LOCATOR:{group_id}",
                })
    payload = {
        "schema": "ovc-lsiac-evidence-dependence-graph/v0.1",
        "generation_id": GENERATION_ID,
        "subject_count": EXPECTED_SUBJECT_COUNT,
        "edges": sorted(edges, key=lambda edge: edge["edge_id"]),
        "authority_effect": "NONE",
    }
    return {**payload, "canonical_sha256": _canonical_sha256(payload)}


def _aggregate_subject(
    subject_id: str,
    passports: list[Mapping[str, Any]],
    delta_entry: Mapping[str, Any] | None,
    dependence_refs: list[str],
) -> dict[str, Any]:
    standings = [str(item["source_standing"]) for item in passports]
    relations = {str(item["source_relation_state"]) for item in passports}
    standing = _weakest(standings, STANDING_WEAKNESS, "SOURCE_STANDING")
    relation = "MULTIPLE_STANDING" if len(set(standings)) > 1 or "MULTIPLE_STANDING" in relations else "CONSISTENT"
    availability = _weakest(
        [str(item["artifact_availability"]) for item in passports],
        AVAILABILITY_WEAKNESS,
        "ARTIFACT_AVAILABILITY",
    )
    reproducibility = _weakest(
        [str(item["reproducibility_class"]) for item in passports],
        REPRODUCIBILITY_WEAKNESS,
        "REPRODUCIBILITY_CLASS",
    )

    disposition = "UNRESOLVED"
    exposure = "UNKNOWN"
    if delta_entry is not None:
        candidate_disposition = str(delta_entry.get("scientific_disposition", "UNRESOLVED"))
        if candidate_disposition in ALLOWED_DISPOSITIONS:
            disposition = candidate_disposition
        candidate_exposure = str(delta_entry.get("exposure_state", "UNKNOWN"))
        if candidate_exposure in ALLOWED_EXPOSURE:
            exposure = candidate_exposure

    blockers: list[str] = []
    if standing == "PENDING_SOURCE_BINDING":
        blockers.append("PENDING_SOURCE_BINDING")
        disposition = "NOT_EVALUABLE"
    elif standing == "SOURCE_DERIVED":
        blockers.append("EXACT_LOAD_BEARING_SOURCE_NOT_BOUND_FOR_STRONGER_CLAIM")
    if availability == "MISSING":
        blockers.append("ARTIFACT_MISSING")
    elif availability == "VERIFIED_ONCE_UNBOUND":
        blockers.append("LOAD_BEARING_RETRIEVABILITY_NOT_ESTABLISHED_IF_REQUIRED")

    return {
        "schema": "ovc-lsiac-pass1-classification/v0.1",
        "generation_id": GENERATION_ID,
        "subject_id": subject_id,
        "source_standing": standing,
        "scientific_disposition": disposition,
        "exposure_state": exposure,
        "source_relation_state": relation,
        "triage_class": "SOURCE_BLOCKED" if standing == "PENDING_SOURCE_BINDING" else "FULL_INDIVIDUAL_REVIEW",
        "artifact_availability": availability,
        "reproducibility_class": reproducibility,
        "dependence_refs": sorted(dependence_refs),
        "source_blockers": sorted(set(blockers)),
        "classification_rationale": (
            "Deterministic GEN0002 Pass-1 projection from the exact frozen source-passport set"
            + (" and exact post-v0.5 delta entry" if delta_entry is not None else "")
            + "; unresolved scientific standing is preserved rather than inferred from names, recurrence, status labels, or inheritance nominations."
        ),
        "authority_effect": "NONE_PASS1_CLASSIFICATION_ONLY",
    }


def build_pass1_classification_view(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    passports = load_source_passports(root)
    delta_by_subject = _post_delta_by_subject(root)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for passport in passports:
        grouped[str(passport["subject_id"])].append(passport)
    if len(grouped) != EXPECTED_SUBJECT_COUNT:
        raise ValueError(f"LSIAC_GEN0002_PASS1_SUBJECT_COUNT_MISMATCH:{len(grouped)}")

    groups = _dependence_groups(passports)
    refs: dict[str, set[str]] = defaultdict(set)
    for group_id, subjects in groups.items():
        for subject_id in subjects:
            refs[subject_id].add(group_id)

    classifications = [
        _aggregate_subject(subject_id, grouped[subject_id], delta_by_subject.get(subject_id), sorted(refs.get(subject_id, set())))
        for subject_id in sorted(grouped)
    ]
    counts: dict[str, dict[str, int]] = {}
    for field in (
        "source_standing", "scientific_disposition", "exposure_state",
        "source_relation_state", "triage_class", "artifact_availability",
        "reproducibility_class",
    ):
        values: dict[str, int] = defaultdict(int)
        for record in classifications:
            values[str(record[field])] += 1
        counts[field] = dict(sorted(values.items()))

    return {
        "schema": "ovc-lsiac-pass1-classification-view/v0.1",
        "programme_id": "OVC-LSIAC-v0.1",
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "subject_count": len(classifications),
        "passport_count": len(passports),
        "classifications": classifications,
        "classification_records_canonical_sha256": _canonical_sha256(classifications),
        "counts": counts,
        "dependence_graph": build_shared_locator_dependence_graph(passports),
        "dependence_group_count": len(groups),
        "dependence_absence_rule": "NO_EDGE_DOES_NOT_ESTABLISH_INDEPENDENCE",
        "pass1_only": True,
        "forbidden_outputs_absent": [
            "FINAL_INHERITANCE_ROLE", "RETAIN_FORWARD", "DESTINATION_BINDING_SET",
            "ARCHITECTURE_EFFECT_SET", "SCIENTIFIC_PROMOTION",
        ],
        "authority_effect": "NONE_PASS1_CLASSIFICATION_ONLY",
    }


def build_virtual_view_identity(*, algorithm_git_blob_sha: str) -> str:
    payload = {
        "schema": "ovc-lsiac-pass1-virtual-view-identity/v0.1",
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "algorithm_git_blob_sha": algorithm_git_blob_sha,
        "projection": "PASS1_SOURCE_STANDING_EXPOSURE_DEPENDENCE_CLASSIFICATION_V1",
        "absence_rule": "NO_DEPENDENCE_EDGE_DOES_NOT_ESTABLISH_INDEPENDENCE",
        "scope": "ALL_431_GEN0002_ACCESSION_SUBJECTS",
    }
    return _canonical_sha256(payload)
