from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Mapping

from ovc.research_operations.canonical import canonical_sha256

from .models import C2Snapshot, PatternDiscoveryError


CONTROL_PACK_VERSION = "PD.CONTROLS.v0.1"


@dataclass(frozen=True)
class ControlSamplingPack:
    pack_id: str = CONTROL_PACK_VERSION
    seed: str = "OVC-PD-CONTROL-001"
    population_denominator: int = 5
    matched_denominator: int = 4

    def __post_init__(self) -> None:
        if self.population_denominator < 1 or self.matched_denominator < 1:
            raise ValueError("control sampling denominators must be positive")


def _selected(identity: Mapping[str, Any], *, denominator: int) -> bool:
    return int(canonical_sha256(identity)[:16], 16) % denominator == 0


def source_control_identity(snapshot: C2Snapshot, pack: ControlSamplingPack, control_class: str) -> dict[str, Any]:
    return {
        "control_pack_id": pack.pack_id,
        "seed": pack.seed,
        "control_class": control_class,
        "source_release_id": snapshot.c2_release_id,
        "source_manifest_id": snapshot.c2_manifest_id,
        "source_c2_record_id": snapshot.c2_state_id,
        "first_valid_time": snapshot.first_valid_time,
        "clock": snapshot.clock,
        "price_side": snapshot.side,
        "scope_id": snapshot.evaluation_scope_id,
        "parent_container_id": snapshot.parent_container_id,
    }


def select_population_control(
    snapshot_record: Mapping[str, Any] | C2Snapshot,
    *,
    pack: ControlSamplingPack = ControlSamplingPack(),
    eligible: bool = True,
) -> dict[str, Any]:
    snapshot = snapshot_record if isinstance(snapshot_record, C2Snapshot) else C2Snapshot.from_mapping(snapshot_record)
    identity = source_control_identity(snapshot, pack, "POPULATION_CONTROL")
    selected = bool(eligible) and _selected(identity, denominator=pack.population_denominator)
    return {
        "control_selection_id": f"PDCTL-{canonical_sha256(identity)[:32]}",
        "control_class": "POPULATION_CONTROL",
        "selected": selected,
        "selection_reason": "DETERMINISTIC_SAMPLE_SELECTION" if selected else "DETERMINISTIC_SAMPLE_NOT_SELECTED",
        "pack_id": pack.pack_id,
        "source_c2_record_id": snapshot.c2_state_id,
        "source_release_id": snapshot.c2_release_id,
        "first_valid_at": snapshot.first_valid_time,
        "matching": None,
    }


def select_matched_control(
    snapshot_record: Mapping[str, Any] | C2Snapshot,
    target_candidate: Mapping[str, Any],
    *,
    broad_structural_regime: str,
    pack: ControlSamplingPack = ControlSamplingPack(),
    target_trigger_fired: bool = False,
) -> dict[str, Any]:
    snapshot = snapshot_record if isinstance(snapshot_record, C2Snapshot) else C2Snapshot.from_mapping(snapshot_record)
    required = {
        "instrument": "GBPUSD",
        "price_side": snapshot.side,
        "clock": snapshot.clock,
        "scope_id": snapshot.evaluation_scope_id,
        "parent_container_id": snapshot.parent_container_id,
        "broad_structural_regime": broad_structural_regime,
    }
    target = {
        "instrument": target_candidate.get("instrument"),
        "price_side": target_candidate.get("price_side"),
        "clock": target_candidate.get("clock"),
        "scope_id": target_candidate.get("scope_id"),
        "parent_container_id": target_candidate.get("parent_container_id"),
        "broad_structural_regime": target_candidate.get("broad_structural_regime"),
    }
    comparable = required == target
    identity = {
        **source_control_identity(snapshot, pack, "MATCHED_CONTROL"),
        "target_candidate_id": target_candidate.get("window_id"),
        "matching": required,
    }
    selected = comparable and not target_trigger_fired and _selected(identity, denominator=pack.matched_denominator)
    reason = "DETERMINISTIC_MATCHED_SELECTION" if selected else (
        "TARGET_TRIGGER_FIRED" if target_trigger_fired else "MATCH_FIELDS_DIFFER" if not comparable else "DETERMINISTIC_SAMPLE_NOT_SELECTED"
    )
    return {
        "control_selection_id": f"PDCTL-{canonical_sha256(identity)[:32]}",
        "control_class": "MATCHED_CONTROL",
        "selected": selected,
        "selection_reason": reason,
        "pack_id": pack.pack_id,
        "source_c2_record_id": snapshot.c2_state_id,
        "source_release_id": snapshot.c2_release_id,
        "first_valid_at": snapshot.first_valid_time,
        "matching": required,
        "target_candidate_id": target_candidate.get("window_id"),
    }


def required_control_counts(total_analytical_population: int) -> dict[str, int]:
    if total_analytical_population < 0:
        raise ValueError("analytical population cannot be negative")
    total_controls = ceil(total_analytical_population * 0.20)
    return {
        "total_controls": total_controls,
        "matched_controls": ceil(total_controls * 0.50),
        "population_controls": ceil(total_controls * 0.25),
    }


def assess_control_representation(total_analytical_population: int, controls: list[Mapping[str, Any]]) -> dict[str, Any]:
    requirements = required_control_counts(total_analytical_population)
    selected = [item for item in controls if item.get("selected")]
    matched = sum(1 for item in selected if item.get("control_class") == "MATCHED_CONTROL")
    population = sum(1 for item in selected if item.get("control_class") == "POPULATION_CONTROL")
    unknown = [item.get("control_class") for item in selected if item.get("control_class") not in {"MATCHED_CONTROL", "POPULATION_CONTROL"}]
    if unknown:
        raise PatternDiscoveryError(f"unknown control classes: {unknown}")
    deficits = {
        "total_controls": max(requirements["total_controls"] - len(selected), 0),
        "matched_controls": max(requirements["matched_controls"] - matched, 0),
        "population_controls": max(requirements["population_controls"] - population, 0),
    }
    return {
        "requirements": requirements,
        "actual": {"total_controls": len(selected), "matched_controls": matched, "population_controls": population},
        "deficits": deficits,
        "status": "PASS" if not any(deficits.values()) else "CONTROL_REPRESENTATION_DEFICIT",
    }
