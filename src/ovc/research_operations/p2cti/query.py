from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .currentness import evaluate_two_point_currentness
from .demand import next_theory_work
from .sources import resolve_owner_predicate


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json"
)
_OWNER_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json"
)
_VISIBILITY_FIELDS = {
    "schema", "consumer_class", "visibility_state", "source_frontier_id",
    "allowed_query_families", "visible_subject_ids", "visible_relation_ids",
    "visible_demand_ids", "allow_history", "allow_aggregate_counts",
    "resolution_state", "authority_effect",
}
_BUNDLE_FIELDS = {
    "authority_effect", "content_sha256", "currentness_evaluation", "duplicate_screen",
    "entries", "generation", "generation_manifest", "historical_generation_disposition",
    "operational_current_pointer_published", "schema", "scientific_payload_copied", "series",
    "source_document_byte_sizes", "source_frontier", "source_reproduction_receipt_id",
    "source_reproduction_sha256",
}
_CURRENT_REFERENCE_SEMANTIC_GENERATION = "v0.1"
_CURRENTNESS_DEGRADING_WARNINGS = frozenset(
    {
        "RELATION_CONSTITUENT_NOT_CURRENT",
        "CROSS_MODE_EXPOSURE_NOT_CURRENT",
        "CROSS_MODE_RELATION_NOT_CURRENT",
        "DEMAND_QUESTION_NOT_CURRENT",
        "CURRENTNESS_UNRESOLVED",
        "VISIBILITY_DENIED",
        "AGGREGATE_VISIBILITY_DENIED",
    }
)
_COMPLETENESS_DEGRADING_WARNINGS = frozenset(
    {
        "RELATION_OWNER_EVIDENCE_UNRESOLVED",
        "RELATION_OWNER_EVIDENCE_CONFLICT",
        "CROSS_MODE_EXPOSURE_UNRESOLVED",
        "CROSS_MODE_EXPOSURE_NOT_CURRENT",
        "CROSS_MODE_FORMAL_CORRESPONDENCE_REQUIRED",
        "CROSS_MODE_RELATION_NOT_CURRENT",
        "DEMAND_QUESTION_NOT_CURRENT",
        "VISIBILITY_DENIED",
        "AGGREGATE_VISIBILITY_DENIED",
    }
)


class QueryValidationError(ValueError):
    """A query cannot be answered without weakening the reference contract."""


def _query_families() -> frozenset[str]:
    registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    families = registry.get("query_families")
    if type(families) is not list or registry.get("silent_truncation") != "FORBIDDEN":
        raise RuntimeError("P2CTI query registry is invalid")
    return frozenset(families)


QUERY_FAMILIES = _query_families()
_OWNER_REGISTRY = json.loads(_OWNER_REGISTRY_PATH.read_text(encoding="utf-8"))


def _closed_string_list(value: Any, name: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str or not item for item in value):
        raise QueryValidationError(f"{name} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise QueryValidationError(f"{name} must not contain duplicates")
    return tuple(sorted(value))


def _validate_bundle(raw: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(raw, Mapping) or set(raw) != _BUNDLE_FIELDS:
            raise ValueError("generation bundle must use the exact closed field set")
        bundle = deepcopy(dict(raw))
        if bundle["schema"] != "ovc-p2ctii-generation-zero-bundle/v0.1":
            raise ValueError("exact canonical generation bundle is required")
        if bundle["operational_current_pointer_published"] is not False:
            raise ValueError("WP4 reference engine cannot publish or consume an operational pointer")
        if bundle["authority_effect"] != "NONE" or bundle["scientific_payload_copied"] is not False:
            raise ValueError("generation bundle crossed the WP4 authority/reference boundary")
        expected_hash = canonical_sha256({key: value for key, value in bundle.items() if key != "content_sha256"})
        if bundle["content_sha256"] != expected_hash:
            raise ValueError("generation bundle content hash mismatch")
        generation = bundle["generation"]
        frontier = bundle["source_frontier"]
        series = bundle["series"]
        currentness = bundle["currentness_evaluation"]
        for name, value in (("generation", generation), ("source_frontier", frontier), ("series", series)):
            if not isinstance(value, Mapping):
                raise ValueError(f"{name} must be an object")
            if value.get("content_sha256") != canonical_sha256(
                {key: item for key, item in value.items() if key != "content_sha256"}
            ):
                raise ValueError(f"{name} content hash mismatch")
        if generation.get("source_frontier_id") != frontier.get("frontier_id"):
            raise ValueError("generation/source-frontier identity mismatch")
        if generation.get("series_id") != series.get("series_id"):
            raise ValueError("generation/series identity mismatch")
        reproduced = evaluate_two_point_currentness(
            series_id=series["series_id"], generation_id=generation["generation_id"],
            prebuild_frontier=frontier, prepublish_frontier=frontier,
        )
        if reproduced != currentness:
            raise ValueError("currentness evaluation does not bind the exact generation frontier")
        if currentness.get("currentness_state") != "CURRENT" or generation.get("completeness_state") != "COMPLETE":
            raise ValueError("reference query requires a complete CURRENT canonical generation")
        entries = bundle["entries"]
        if type(entries) is not list:
            raise ValueError("entries must be an array")
        entry_ids = []
        for entry in entries:
            if not isinstance(entry, Mapping) or entry.get("content_sha256") != canonical_sha256(
                {key: value for key, value in entry.items() if key != "content_sha256"}
            ):
                raise ValueError("entry content hash mismatch")
            if entry.get("currentness_state") != "CURRENT":
                raise ValueError("stale entry cannot enter the current query generation")
            entry_ids.append(entry.get("entry_id"))
        if len(entry_ids) != len(set(entry_ids)) or sorted(entry_ids) != sorted(generation.get("member_entry_ids", [])):
            raise ValueError("generation membership does not bind the exact entry set")
        return bundle
    except (KeyError, TypeError, ValueError) as exc:
        raise QueryValidationError(str(exc)) from exc


def _validate_visibility(raw: Mapping[str, Any], frontier_id: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _VISIBILITY_FIELDS:
        raise QueryValidationError("explicit closed visibility context is required")
    value = deepcopy(dict(raw))
    if value["schema"] != "ovc-p2cti-query-visibility-context/v0.1":
        raise QueryValidationError("visibility context schema mismatch")
    if value["source_frontier_id"] != frontier_id:
        raise QueryValidationError("visibility context is stale for this source frontier")
    if value["resolution_state"] != "RESOLVED" or value["authority_effect"] != "NONE":
        raise QueryValidationError("visibility authority is unresolved or exceeds WP4")
    if value["visibility_state"] not in {"REFERENCE_ONLY", "RESTRICTED"}:
        raise QueryValidationError("unknown visibility_state")
    if type(value["consumer_class"]) is not str or not value["consumer_class"]:
        raise QueryValidationError("consumer_class is required")
    allowed = _closed_string_list(value["allowed_query_families"], "allowed_query_families")
    if not set(allowed).issubset(QUERY_FAMILIES):
        raise QueryValidationError("visibility context contains an unknown query family")
    for name in ("visible_subject_ids", "visible_relation_ids", "visible_demand_ids"):
        value[name] = _closed_string_list(value[name], name)
    for name in ("allow_history", "allow_aggregate_counts"):
        if type(value[name]) is not bool:
            raise QueryValidationError(f"{name} must be boolean")
    value["allowed_query_families"] = allowed
    return value


def _record_id(record: Mapping[str, Any]) -> str | None:
    payload = record.get("payload", {})
    return next((payload.get(name) for name in ("relation_id", "screen_id", "ambiguity_id", "conflict_id") if payload.get(name)), None)


def _canonical_record_key(record: Mapping[str, Any]) -> tuple[str, ...]:
    payload = record.get("payload", {})
    left = payload.get("left_generation_ref", {})
    right = payload.get("right_generation_ref", {})
    return (
        str(record.get("object_type", "")),
        str(payload.get("relation_family", "")),
        str(payload.get("relation_type", "")),
        str(left.get("object_id", "")),
        str(left.get("semantic_generation", "")),
        str(right.get("object_id", "")),
        str(right.get("semantic_generation", "")),
        str(_record_id(record) or payload.get("demand_id", "")),
        str(record.get("record_id", "")),
        str(record.get("content_sha256", "")),
    )


def _relation_constituent_warnings(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    warnings: set[str] = set()
    for row in rows:
        payload = row.get("payload", {})
        if payload.get("current_generation_binding") != "CURRENT":
            warnings.add("RELATION_CONSTITUENT_NOT_CURRENT")
        evidence_state = payload.get("owner_evidence_state")
        if evidence_state == "CONFLICT":
            warnings.add("RELATION_OWNER_EVIDENCE_CONFLICT")
        elif evidence_state != "RESOLVED":
            warnings.add("RELATION_OWNER_EVIDENCE_UNRESOLVED")
        raw = payload.get("warnings", [])
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            warnings.update(str(item) for item in raw if type(item) is str and item)
    return sorted(warnings)


class ReferenceQueryEngine:
    """Read-only semantic oracle for WP4 reference query behavior."""

    def __init__(
        self, *, generation_bundle: Mapping[str, Any], relations: Sequence[Mapping[str, Any]] = (),
        duplicate_screens: Sequence[Mapping[str, Any]] = (), demands: Sequence[Mapping[str, Any]] = (),
        historical_generations: Sequence[Mapping[str, Any]] = (),
        visibility_context: Mapping[str, Any] | None = None,
        exposure_owner_evidence: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self._bundle = _validate_bundle(generation_bundle)
        frontier_id = self._bundle["generation"]["source_frontier_id"]
        self._visibility = _validate_visibility(visibility_context, frontier_id)
        self._entries = tuple(sorted(deepcopy(self._bundle["entries"]), key=lambda row: row["entry_id"]))
        self._relations = tuple(sorted(deepcopy(list(relations)), key=_canonical_record_key))
        self._screens = tuple(sorted(deepcopy(list(duplicate_screens)), key=_canonical_record_key))
        self._demands = tuple(sorted(deepcopy(list(demands)), key=_canonical_record_key))
        self._history = tuple(
            sorted(
                deepcopy(list(historical_generations)),
                key=lambda row: (
                    str(row.get("generation_id", "")),
                    str(row.get("generation_ordinal", "")),
                ),
            )
        )
        for collection_name, collection in (
            ("relations", self._relations), ("duplicate_screens", self._screens),
            ("demands", self._demands),
        ):
            for record in collection:
                if not isinstance(record, Mapping) or record.get("source_frontier_id") != frontier_id:
                    raise QueryValidationError(f"{collection_name} contain stale or malformed records")
                if record.get("content_sha256") != canonical_sha256(
                    {key: value for key, value in record.items() if key != "content_sha256"}
                ):
                    raise QueryValidationError(f"{collection_name} record content hash mismatch")
        current_generation = self._bundle["generation"]
        seen_history: set[tuple[Any, Any]] = set()
        for item in self._history:
            if not isinstance(item, Mapping):
                raise QueryValidationError("historical generation must be an object")
            identity = (item.get("generation_id"), item.get("generation_ordinal"))
            if None in identity or identity in seen_history:
                raise QueryValidationError("historical generation identity is malformed or duplicated")
            if item.get("generation_id") == current_generation["generation_id"]:
                raise QueryValidationError("current generation cannot also be historical")
            if item.get("generation_ordinal") == current_generation["generation_ordinal"]:
                raise QueryValidationError("historical/current generation ordinal collision")
            seen_history.add(identity)
        try:
            self._exposure = resolve_owner_predicate(
                object_type="DMRP_EXPOSURE", predicate="PATH1_PATH2_EXPOSURE",
                evidence=exposure_owner_evidence, owner_registry=_OWNER_REGISTRY,
            )
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(f"cross-mode exposure evidence is invalid: {exc}") from exc

    def _entry(self, subject_id: str) -> Mapping[str, Any] | None:
        if subject_id not in self._visibility["visible_subject_ids"]:
            return None
        return next((entry for entry in self._entries if entry["subject_id"] == subject_id), None)

    def _demand(self, demand_id: str) -> Mapping[str, Any] | None:
        if demand_id not in self._visibility["visible_demand_ids"]:
            return None
        return next((row for row in self._demands if row.get("payload", {}).get("demand_id") == demand_id), None)

    def _visible_relation(self, row: Mapping[str, Any]) -> bool:
        identity = _record_id(row)
        if identity not in self._visibility["visible_relation_ids"]:
            return False
        refs = row.get("payload", {}).get("subject_refs")
        if refs is None:
            refs = [
                row.get("payload", {}).get("left_generation_ref", {}),
                row.get("payload", {}).get("right_generation_ref", {}),
            ]
        subject_ids = {ref.get("object_id") for ref in refs if isinstance(ref, Mapping)}
        return subject_ids.issubset(set(self._visibility["visible_subject_ids"]))

    def _visible_demand(self, row: Mapping[str, Any]) -> bool:
        return row.get("payload", {}).get("demand_id") in self._visibility["visible_demand_ids"]

    def _envelope(self, family: str, result: Any, warnings: Sequence[str] = ()) -> dict[str, Any]:
        generation = self._bundle["generation"]
        currentness = self._bundle["currentness_evaluation"]
        combined_warnings = sorted(set([*currentness.get("warnings", []), *warnings]))
        currentness_state = currentness["currentness_state"]
        completeness_state = generation["completeness_state"]
        if _CURRENTNESS_DEGRADING_WARNINGS.intersection(combined_warnings):
            currentness_state = "REASSESSMENT_REQUIRED"
        if _COMPLETENESS_DEGRADING_WARNINGS.intersection(combined_warnings):
            completeness_state = "UNRESOLVED"
        return deepcopy({
            "schema": "ovc-p2cti-reference-query-result/v0.1",
            "query_family": family,
            "generation_id": generation["generation_id"],
            "source_frontier_id": generation["source_frontier_id"],
            "currentness_state": currentness_state,
            "visibility_state": self._visibility["visibility_state"],
            "completeness_state": completeness_state,
            "warnings": combined_warnings,
            "ambiguity_state": "UNRESOLVED" if "RELATION_AMBIGUITY_UNRESOLVED" in combined_warnings else "NONE_VISIBLE",
            "conflict_state": "BLOCKING" if any(
                warning in combined_warnings
                for warning in ("RELATION_CONFLICT_BLOCKING", "RELATION_OWNER_EVIDENCE_CONFLICT")
            ) else "NONE_VISIBLE",
            "result": result,
            "read_only": True,
            "decision_bearing": False,
            "semantic_promotion": False,
            "authority_effect": "NONE",
        })

    @staticmethod
    def _bounded(rows: list[Any], limit: int | None) -> tuple[list[Any], list[str], dict[str, Any] | None]:
        if limit is None:
            return rows, [], None
        if type(limit) is not int or limit < 1:
            raise QueryValidationError("limit must be a positive integer")
        if len(rows) <= limit:
            return rows, [], None
        return rows[:limit], ["RESULT_SET_TRUNCATED_EXPLICITLY"], {
            "returned": limit, "available": len(rows), "silent": False
        }

    def query(self, family: str, **params: Any) -> dict[str, Any]:
        if family not in QUERY_FAMILIES:
            raise QueryValidationError(f"unknown query family: {family}")
        if family not in self._visibility["allowed_query_families"]:
            return self._envelope(family, None, ["VISIBILITY_DENIED"])
        warnings: list[str] = []
        if family == "SEARCH":
            text = params.get("text")
            if type(text) is not str or not text:
                raise QueryValidationError("SEARCH requires non-empty text")
            rows = [
                {"subject_id": entry["subject_id"], "entry_id": entry["entry_id"],
                 "retrieval_authority": "ADVISORY_ONLY"}
                for entry in self._entries
                if entry["subject_id"] in self._visibility["visible_subject_ids"]
                and text.casefold() in entry["subject_id"].casefold()
            ]
            rows, warnings, truncation = self._bounded(rows, params.get("limit"))
            result = {"matches": rows, "truncation": truncation}
        elif family == "GET_THEORY":
            entry = self._entry(params.get("subject_id"))
            result = None if entry is None else {
                "inventory_entry": entry,
                "scientific_payload": "OWNER_REFERENCE_ONLY_NOT_COPIED",
            }
        elif family == "WHY_HERE":
            entry = self._entry(params.get("subject_id"))
            result = None if entry is None else {
                "subject_id": entry["subject_id"],
                "source_object_ref": entry["source_object_ref"],
                "source_locator": entry["source_locator"],
                "reason_codes": ["GENERATION_ZERO_SOURCE_CENSUS_MEMBER"],
            }
        elif family == "CURRENT_STATE":
            entry = self._entry(params.get("subject_id"))
            result = None if entry is None else {
                "subject_id": entry["subject_id"],
                "capture_state": entry["capture_state"],
                "currentness_state": entry["currentness_state"],
                "authority_refs": entry["authority_refs"],
                "orthogonal_state_inference": False,
            }
        elif family == "HISTORY":
            if not self._visibility["allow_history"]:
                return self._envelope(family, [], ["VISIBILITY_DENIED"])
            rows = [
                {"generation_id": item["generation_id"], "generation_ordinal": item["generation_ordinal"],
                 "disposition": "HISTORICAL_RETAINED_ADDRESSABLE"}
                for item in self._history
            ]
            rows.append({
                "generation_id": self._bundle["generation"]["generation_id"],
                "generation_ordinal": self._bundle["generation"]["generation_ordinal"],
                "disposition": "CURRENT_REFERENCE_GENERATION",
            })
            result = sorted(rows, key=lambda row: (row["generation_ordinal"], row["generation_id"]))
        elif family == "RELATIONS":
            subject_id = params.get("subject_id")
            direct = [row for row in self._relations if row.get("object_type") == "THEORY_RELATION" and self._visible_relation(row) and subject_id in {
                row.get("payload", {}).get("left_generation_ref", {}).get("object_id"),
                row.get("payload", {}).get("right_generation_ref", {}).get("object_id"),
            }]
            ambiguities = [row for row in self._relations if row.get("object_type") == "RELATION_AMBIGUITY" and self._visible_relation(row) and subject_id in {
                ref.get("object_id") for ref in row.get("payload", {}).get("subject_refs", [])
            }]
            conflicts = [row for row in self._relations if row.get("object_type") == "RELATION_CONFLICT" and self._visible_relation(row) and subject_id in {
                ref.get("object_id") for ref in row.get("payload", {}).get("subject_refs", [])
            }]
            direct, warnings, truncation = self._bounded(direct, params.get("limit"))
            warnings.extend(_relation_constituent_warnings(direct))
            if ambiguities:
                warnings.append("RELATION_AMBIGUITY_UNRESOLVED")
            if conflicts:
                warnings.append("RELATION_CONFLICT_BLOCKING")
            result = {"relations": direct, "ambiguities": ambiguities, "conflicts": conflicts, "truncation": truncation}
        elif family == "DUPLICATE_SCREEN":
            subject_id = params.get("subject_id")
            rows = [row for row in self._screens if self._visible_relation(row) and subject_id in {
                ref.get("object_id") for ref in row.get("payload", {}).get("subject_refs", [])
            }]
            result = {"screens": rows, "identity_collapse_allowed": False}
        elif family == "OPEN_DEMAND":
            result = [row for row in self._demands if self._visible_demand(row) and row.get("payload", {}).get("status") == "OPEN"]
            if any(row.get("payload", {}).get("research_question_status") != "CURRENT" for row in result):
                warnings.append("DEMAND_QUESTION_NOT_CURRENT")
        elif family == "WHY_BLOCKED":
            demand = self._demand(params.get("demand_id"))
            result = None if demand is None else {
                "demand_id": demand["payload"]["demand_id"],
                "status": demand["payload"]["status"],
                "reason_codes": sorted(set(params.get("reason_codes", []))),
            }
        elif family == "UNBLOCK_PATH":
            demand = self._demand(params.get("demand_id"))
            result = None if demand is None else {
                "demand_id": demand["payload"]["demand_id"],
                "required_evidence_refs": sorted(set(params.get("required_evidence_refs", []))),
                "advisory_only": True,
            }
        elif family == "NEXT_THEORY_WORK":
            result = next_theory_work(
                demand_records=[row for row in self._demands if self._visible_demand(row)],
                eligibility=params.get("eligibility", {}),
                authority_refs=params.get("authority_refs", []),
                preference_classes=params.get("preference_classes"),
            )
        elif family == "ARCHITECTURE_NEED":
            result = [row for row in self._demands if self._visible_demand(row) and row.get("payload", {}).get("demand_class") == "ARCHITECTURE_NEED_HYPOTHESIS"]
            if any(row.get("payload", {}).get("research_question_status") != "CURRENT" for row in result):
                warnings.append("DEMAND_QUESTION_NOT_CURRENT")
        elif family == "CROSS_MODE":
            exposure_source = self._exposure.get("resolved_source")
            if self._exposure["resolution_state"] != "RESOLVED":
                result = []
                warnings.append("CROSS_MODE_EXPOSURE_UNRESOLVED")
            elif (
                not isinstance(exposure_source, Mapping)
                or exposure_source.get("semantic_generation") != _CURRENT_REFERENCE_SEMANTIC_GENERATION
            ):
                result = []
                warnings.append("CROSS_MODE_EXPOSURE_NOT_CURRENT")
            else:
                candidates = [
                    row for row in self._relations
                    if self._visible_relation(row)
                    and row.get("payload", {}).get("relation_family") == "CROSS_MODE"
                ]
                result = [
                    row for row in candidates
                    if row.get("payload", {}).get("current_generation_binding") == "CURRENT"
                    and row.get("payload", {}).get("owner_evidence_state") == "RESOLVED"
                    and row.get("payload", {}).get("admission_disposition") == "ADMITTED_REVIEWED"
                    and row.get("payload", {}).get("qualification") in {
                        "INDEPENDENT_RULE_REVIEWED", "HUMAN_RESEARCH_OPERATIONS_DECISION"
                    }
                ]
                if any(
                    row.get("payload", {}).get("current_generation_binding") != "CURRENT"
                    for row in candidates
                ):
                    warnings.append("CROSS_MODE_RELATION_NOT_CURRENT")
                if len(result) != len(candidates):
                    warnings.append("CROSS_MODE_FORMAL_CORRESPONDENCE_REQUIRED")
        elif family == "PORTFOLIO_STATE":
            if not self._visibility["allow_aggregate_counts"]:
                result = None
                warnings.append("AGGREGATE_VISIBILITY_DENIED")
            else:
                visible_entries = [entry for entry in self._entries if entry["subject_id"] in self._visibility["visible_subject_ids"]]
                visible_demands = [row for row in self._demands if self._visible_demand(row)]
                result = {
                    "entry_class_counts": dict(sorted(Counter(entry["subject_class"] for entry in visible_entries).items())),
                    "demand_class_counts": dict(sorted(Counter(row["payload"]["demand_class"] for row in visible_demands).items())),
                    "demand_status_counts": dict(sorted(Counter(row["payload"]["status"] for row in visible_demands).items())),
                    "composite_score": None,
                    "dimensions_separate": True,
                }
        else:  # pragma: no cover - registry and branch set are asserted together
            raise QueryValidationError(f"unimplemented query family: {family}")
        return self._envelope(family, result, warnings)
