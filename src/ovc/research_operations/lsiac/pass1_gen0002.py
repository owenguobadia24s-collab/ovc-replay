from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

SOURCE_CENSUS_DIR = Path("docs/programmes/lsiac-v0-1/source-census")
PASSPORT_SUMMARY = SOURCE_CENSUS_DIR / "LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"
POST_DELTA = SOURCE_CENSUS_DIR / "LSIAC_POST_V0_5_DELTA_MANIFEST_v0_1.json"

EXPECTED_SUBJECT_COUNT = 431
EXPECTED_PASSPORT_COUNT = 434
EXPECTED_SOURCE_PASSPORT_SET_SHA256 = "f97ba927944326864f1a5cc20ecc69a0a4623743231aa8479d713984bbe68019"
EXPECTED_POST_DELTA_SHA256 = "1ed67410854478b2947d62055b3b619ad8081c782907c66efa78bbf1d823a42d"
EXPECTED_SOURCE_UNIVERSE_ID = "d29e1c69399d6f312a7e0544c57e2e47c415f37347760f11ce983b926988114c"
EXPECTED_FRONTIER_RECEIPT_ID = "022f6cf4149265cc545e6cffc2d0623a513ec2bf1ab38434c793bbf381a92bbe"
EXPECTED_PROTOCOL_BINDING_ID = "15e449ffe15ded1d6419533257515ab9686122a1b5c73f7c82c49cea6e273d4f"
GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
PROTOCOL_ID = "OVC-LSIAC-ACCESSION-ADJUDICATION-PROTOCOL-0.1"
PACKET_ID = "LSIAC-GEN0002-PASS1-SOURCE-STANDING-EXPOSURE-DEPENDENCE"
PROJECTION = "GEN0002_PASS1_SOURCE_STANDING_EXPOSURE_DEPENDENCE_CLASSIFICATION_V1"

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
    "SUPPORTED_SCOPED",
    "NEGATIVE_SUPPORTED",
    "PARTIAL",
    "REPRESENTATION_DEPENDENT",
    "METHOD_DEPENDENT",
    "TEMPORALLY_HETEROGENEOUS",
    "UNRESOLVED",
    "NOT_EVALUABLE",
}
ALLOWED_EXPOSURE = {
    "FRESH_UNTOUCHED",
    "DISCOVERY_EXPOSED",
    "DEVELOPMENT_EXPOSED",
    "POST_HOC",
    "CONTAMINATED",
    "UNKNOWN",
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


def _weakest(values: Iterable[str], order: Mapping[str, int], label: str) -> str:
    values = list(values)
    if not values:
        raise ValueError(f"LSIAC_GEN0002_PASS1_{label}_EMPTY")
    unknown = set(values) - set(order)
    if unknown:
        raise ValueError(f"LSIAC_GEN0002_PASS1_{label}_UNKNOWN:{sorted(unknown)}")
    return min(values, key=lambda value: order[value])


def load_source_passports(root: str | Path) -> list[dict[str, Any]]:
    """Reconstruct the exact frozen passport set without scientific inference."""
    root = Path(root)
    summary = _load_json(root / PASSPORT_SUMMARY)
    if int(summary.get("passport_count", -1)) != EXPECTED_PASSPORT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_COUNT_MISMATCH")
    if summary.get("full_passport_set_canonical_sha256") != EXPECTED_SOURCE_PASSPORT_SET_SHA256:
        raise ValueError("LSIAC_GEN0002_PASS1_SOURCE_PASSPORT_SET_IDENTITY_MISMATCH")

    field_order = list(summary["field_order"])
    codebooks = summary["codebooks"]
    defaults = dict(summary["defaults"])
    inv = {name: _invert(mapping) for name, mapping in codebooks.items() if isinstance(mapping, Mapping)}

    passports: list[dict[str, Any]] = []
    for chunk_meta in summary["chunks"]:
        chunk = _load_json(root / SOURCE_CENSUS_DIR / str(chunk_meta["file"]))
        rows = chunk.get("rows")
        if not isinstance(rows, list) or len(rows) != int(chunk_meta["count"]):
            raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_CHUNK_COUNT_MISMATCH")
        if chunk.get("h") != chunk_meta.get("canonical_sha256"):
            raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_CHUNK_IDENTITY_MISMATCH")
        for row in rows:
            if not isinstance(row, list) or len(row) < 9:
                raise ValueError("LSIAC_GEN0002_PASS1_PASSPORT_ROW_INVALID")
            raw = dict(zip(field_order, list(row) + [None] * max(0, len(field_order) - len(row))))
            decoded = dict(defaults)
            decoded.update(
                {
                    "passport_id": str(raw["id_suffix"]),
                    "subject_id": str(raw["subject_ref"]),
                    "source_standing": inv["standing"][int(raw["standing"])],
                    "artifact_availability": inv["availability"][int(raw["availability"])],
                    "locator_kind": inv["locator_kind"][int(raw["locator_kind"])],
                    "locator_value": raw["locator_value"],
                    "retention": inv["retention"][int(raw["retention"])],
                    "reproducibility_class": inv["reproducibility"][int(raw["reproducibility"])],
                    "source_relation_state": inv["relation"][int(raw["relation"])],
                }
            )
            extras = raw.get("extras")
            if isinstance(extras, Mapping):
                for key, value in extras.items():
                    if key in {"authority", "exposure"} and isinstance(value, int):
                        decoded[key] = inv[key][value]
                    else:
                        decoded[key] = value
            passports.append(decoded)

    if len(passports) != EXPECTED_PASSPORT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_RECONSTRUCTED_PASSPORT_COUNT_MISMATCH")
    if len({str(passport["subject_id"]) for passport in passports}) != EXPECTED_SUBJECT_COUNT:
        raise ValueError("LSIAC_GEN0002_PASS1_RECONSTRUCTED_SUBJECT_COUNT_MISMATCH")
    return passports


def _post_delta_by_subject(root: Path) -> dict[str, Mapping[str, Any]]:
    delta = _load_json(root / POST_DELTA)
    if delta.get("canonical_manifest_sha256") != EXPECTED_POST_DELTA_SHA256:
        raise ValueError("LSIAC_GEN0002_PASS1_POST_DELTA_IDENTITY_MISMATCH")
    entries = delta.get("entries")
    if not isinstance(entries, list):
        raise ValueError("LSIAC_GEN0002_PASS1_POST_DELTA_ENTRIES_INVALID")
    return {str(entry["subject_id"]): entry for entry in entries if isinstance(entry, Mapping)}


def _normalize_locator(value: object) -> str | None:
    if value is None:
        return None
    token = " ".join(str(value).split()).strip()
    return token or None


def _locator_dependence_groups(passports: list[Mapping[str, Any]]) -> dict[str, list[str]]:
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


def _aggregate_subject(
    subject_id: str,
    passports: list[Mapping[str, Any]],
    delta_entry: Mapping[str, Any] | None,
    dependence_refs: list[str],
) -> dict[str, Any]:
    standings = [str(p["source_standing"]) for p in passports]
    relations = {str(p["source_relation_state"]) for p in passports}
    source_standing = _weakest(standings, STANDING_WEAKNESS, "SOURCE_STANDING")
    source_relation = "MULTIPLE_STANDING" if len(set(standings)) > 1 or "MULTIPLE_STANDING" in relations else "CONSISTENT"
    artifact_availability = _weakest(
        [str(p["artifact_availability"]) for p in passports], AVAILABILITY_WEAKNESS, "ARTIFACT_AVAILABILITY"
    )
    reproducibility_class = _weakest(
        [str(p["reproducibility_class"]) for p in passports], REPRODUCIBILITY_WEAKNESS, "REPRODUCIBILITY_CLASS"
    )

    scientific_disposition = "UNRESOLVED"
    exposure_state = "UNKNOWN"
    if delta_entry is not None:
        disposition = str(delta_entry.get("scientific_disposition", "UNRESOLVED"))
        exposure = str(delta_entry.get("exposure_state", "UNKNOWN"))
        scientific_disposition = disposition if disposition in ALLOWED_DISPOSITIONS else "UNRESOLVED"
        exposure_state = exposure if exposure in ALLOWED_EXPOSURE else "UNKNOWN"

    source_blockers: list[str] = []
    if source_standing == "PENDING_SOURCE_BINDING":
        scientific_disposition = "NOT_EVALUABLE"
        source_blockers.append("PENDING_SOURCE_BINDING")
    elif source_standing == "SOURCE_DERIVED":
        source_blockers.append("EXACT_LOAD_BEARING_SOURCE_NOT_BOUND_FOR_STRONGER_CLAIM")
    if artifact_availability == "MISSING":
        source_blockers.append("ARTIFACT_MISSING")
    elif artifact_availability == "VERIFIED_ONCE_UNBOUND":
        source_blockers.append("LOAD_BEARING_RETRIEVABILITY_NOT_ESTABLISHED_IF_REQUIRED")

    return {
        "schema": "ovc-lsiac-gen0002-pass1-classification/v0.1",
        "generation_id": GENERATION_ID,
        "subject_id": subject_id,
        "source_standing": source_standing,
        "scientific_disposition": scientific_disposition,
        "exposure_state": exposure_state,
        "source_relation_state": source_relation,
        "triage_class": "SOURCE_BLOCKED" if source_standing == "PENDING_SOURCE_BINDING" else "FULL_INDIVIDUAL_REVIEW",
        "artifact_availability": artifact_availability,
        "reproducibility_class": reproducibility_class,
        "passport_count": len(passports),
        "dependence_refs": sorted(dependence_refs),
        "source_blockers": sorted(set(source_blockers)),
        "classification_rationale": (
            "Deterministic GEN0002 Pass-1 projection from the operator-authorised corrected accounting frontier; "
            "scientific disposition/exposure are preserved only when exact post-v0.5 delta fields already support them."
        ),
        "authority_effect": "NONE_PASS1_CLASSIFICATION_ONLY",
    }


def build_shared_locator_dependence_graph(passports: list[Mapping[str, Any]]) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    for group_id, ordered in sorted(_locator_dependence_groups(passports).items()):
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                edges.append(
                    {
                        "edge_id": "EDGE-" + hashlib.sha256(f"{group_id}|{left}|{right}".encode("utf-8")).hexdigest()[:24],
                        "left_subject_id": left,
                        "right_subject_id": right,
                        "dependence_class": "SHARED_SOURCE_DEPENDENT",
                        "basis": f"IDENTICAL_FROZEN_SOURCE_LOCATOR:{group_id}",
                    }
                )
    payload = {
        "schema": "ovc-lsiac-evidence-dependence-graph/v0.1",
        "generation_id": GENERATION_ID,
        "subject_count": EXPECTED_SUBJECT_COUNT,
        "edges": sorted(edges, key=lambda edge: edge["edge_id"]),
        "authority_effect": "NONE",
    }
    return {**payload, "canonical_sha256": _canonical_sha256(payload)}


def build_pass1_classification_view(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    passports = load_source_passports(root)
    delta_by_subject = _post_delta_by_subject(root)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for passport in passports:
        grouped[str(passport["subject_id"])].append(passport)
    if len(grouped) != EXPECTED_SUBJECT_COUNT:
        raise ValueError(f"LSIAC_GEN0002_PASS1_SUBJECT_COUNT_MISMATCH:{len(grouped)}")

    dependence_groups = _locator_dependence_groups(passports)
    refs_by_subject: dict[str, set[str]] = defaultdict(set)
    for group_id, subjects in dependence_groups.items():
        for subject in subjects:
            refs_by_subject[subject].add(group_id)

    classifications = [
        _aggregate_subject(subject_id, grouped[subject_id], delta_by_subject.get(subject_id), sorted(refs_by_subject.get(subject_id, set())))
        for subject_id in sorted(grouped)
    ]
    counts: dict[str, dict[str, int]] = {}
    for field in (
        "source_standing",
        "scientific_disposition",
        "exposure_state",
        "source_relation_state",
        "triage_class",
        "artifact_availability",
        "reproducibility_class",
    ):
        values: dict[str, int] = defaultdict(int)
        for record in classifications:
            values[str(record[field])] += 1
        counts[field] = dict(sorted(values.items()))

    return {
        "schema": "ovc-lsiac-gen0002-pass1-classification-view/v0.1",
        "programme_id": "OVC-LSIAC-v0.1",
        "packet_id": PACKET_ID,
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "source_universe_id": EXPECTED_SOURCE_UNIVERSE_ID,
        "frontier_receipt_id": EXPECTED_FRONTIER_RECEIPT_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "subject_count": len(classifications),
        "passport_count": len(passports),
        "classifications": classifications,
        "classification_records_canonical_sha256": _canonical_sha256(classifications),
        "counts": counts,
        "dependence_graph": build_shared_locator_dependence_graph(passports),
        "dependence_group_count": len(dependence_groups),
        "dependence_absence_rule": "NO_EDGE_DOES_NOT_ESTABLISH_INDEPENDENCE",
        "pass1_only": True,
        "forbidden_outputs_absent": [
            "FINAL_INHERITANCE_ROLE",
            "RETAIN_FORWARD",
            "DESTINATION_BINDING_SET",
            "ARCHITECTURE_EFFECT_SET",
            "SCIENTIFIC_PROMOTION",
        ],
        "authority_effect": "NONE_PASS1_CLASSIFICATION_ONLY",
    }


def build_virtual_view_identity(*, algorithm_git_blob_sha: str) -> str:
    payload = {
        "schema": "ovc-lsiac-gen0002-pass1-virtual-view-identity/v0.1",
        "generation_id": GENERATION_ID,
        "protocol_id": PROTOCOL_ID,
        "source_universe_id": EXPECTED_SOURCE_UNIVERSE_ID,
        "frontier_receipt_id": EXPECTED_FRONTIER_RECEIPT_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "source_passport_set_sha256": EXPECTED_SOURCE_PASSPORT_SET_SHA256,
        "post_v0_5_delta_sha256": EXPECTED_POST_DELTA_SHA256,
        "algorithm_git_blob_sha": algorithm_git_blob_sha,
        "projection": PROJECTION,
        "absence_rule": "NO_DEPENDENCE_EDGE_DOES_NOT_ESTABLISH_INDEPENDENCE",
        "scope": "ALL_431_GEN0002_FROZEN_ACCESSION_SUBJECTS",
    }
    return _canonical_sha256(payload)
