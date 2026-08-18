from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from .demand import next_theory_work


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json"
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


class ReferenceQueryEngine:
    """Read-only semantic oracle for WP4 reference query behavior."""

    def __init__(
        self, *, generation_bundle: Mapping[str, Any], relations: Sequence[Mapping[str, Any]] = (),
        duplicate_screens: Sequence[Mapping[str, Any]] = (), demands: Sequence[Mapping[str, Any]] = (),
        historical_generations: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        if generation_bundle.get("schema") != "ovc-p2ctii-generation-zero-bundle/v0.1":
            raise QueryValidationError("exact canonical generation bundle is required")
        if generation_bundle.get("operational_current_pointer_published") is not False:
            raise QueryValidationError("WP4 reference engine cannot publish or consume an operational pointer")
        self._bundle = dict(generation_bundle)
        self._entries = tuple(generation_bundle["entries"])
        self._relations = tuple(relations)
        self._screens = tuple(duplicate_screens)
        self._demands = tuple(demands)
        self._history = tuple(historical_generations)

    def _entry(self, subject_id: str) -> Mapping[str, Any] | None:
        return next((entry for entry in self._entries if entry["subject_id"] == subject_id), None)

    def _demand(self, demand_id: str) -> Mapping[str, Any] | None:
        return next((row for row in self._demands if row.get("payload", {}).get("demand_id") == demand_id), None)

    def _envelope(self, family: str, result: Any, warnings: Sequence[str] = ()) -> dict[str, Any]:
        generation = self._bundle["generation"]
        currentness = self._bundle["currentness_evaluation"]
        return {
            "schema": "ovc-p2cti-reference-query-result/v0.1",
            "query_family": family,
            "generation_id": generation["generation_id"],
            "source_frontier_id": generation["source_frontier_id"],
            "currentness_state": currentness["currentness_state"],
            "visibility_state": currentness["visibility_state"],
            "completeness_state": generation["completeness_state"],
            "warnings": sorted(set([*currentness.get("warnings", []), *warnings])),
            "result": result,
            "read_only": True,
            "decision_bearing": False,
            "semantic_promotion": False,
            "authority_effect": "NONE",
        }

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
        warnings: list[str] = []
        if family == "SEARCH":
            text = params.get("text")
            if type(text) is not str or not text:
                raise QueryValidationError("SEARCH requires non-empty text")
            rows = [
                {"subject_id": entry["subject_id"], "entry_id": entry["entry_id"],
                 "retrieval_authority": "ADVISORY_ONLY"}
                for entry in self._entries if text.casefold() in entry["subject_id"].casefold()
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
            rows = [row for row in self._relations if subject_id in {
                row.get("payload", {}).get("left_generation_ref", {}).get("object_id"),
                row.get("payload", {}).get("right_generation_ref", {}).get("object_id"),
            }]
            rows, warnings, truncation = self._bounded(rows, params.get("limit"))
            result = {"relations": rows, "truncation": truncation}
        elif family == "DUPLICATE_SCREEN":
            subject_id = params.get("subject_id")
            rows = [row for row in self._screens if subject_id in {
                ref.get("object_id") for ref in row.get("payload", {}).get("subject_refs", [])
            }]
            result = {"screens": rows, "identity_collapse_allowed": False}
        elif family == "OPEN_DEMAND":
            result = [row for row in self._demands if row.get("payload", {}).get("status") == "OPEN"]
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
                demand_records=self._demands,
                eligibility=params.get("eligibility", {}),
                authority_refs=params.get("authority_refs", []),
                preference_classes=params.get("preference_classes"),
            )
        elif family == "ARCHITECTURE_NEED":
            result = [row for row in self._demands if row.get("payload", {}).get("demand_class") == "ARCHITECTURE_NEED_HYPOTHESIS"]
        elif family == "CROSS_MODE":
            result = [row for row in self._relations if row.get("payload", {}).get("relation_family") == "CROSS_MODE"]
        elif family == "PORTFOLIO_STATE":
            result = {
                "entry_class_counts": dict(sorted(Counter(entry["subject_class"] for entry in self._entries).items())),
                "demand_class_counts": dict(sorted(Counter(row["payload"]["demand_class"] for row in self._demands).items())),
                "demand_status_counts": dict(sorted(Counter(row["payload"]["status"] for row in self._demands).items())),
                "composite_score": None,
                "dimensions_separate": True,
            }
        else:  # pragma: no cover - registry and branch set are asserted together
            raise QueryValidationError(f"unimplemented query family: {family}")
        return self._envelope(family, result, warnings)
