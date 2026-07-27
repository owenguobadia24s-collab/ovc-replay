from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ovc.research_operations.canonical import canonical_sha256

from .models import PatternDiscoveryError


NOVELTY_VERSION = "PD.NOVELTY_SHADOW.v0.1"
NOVELTY_STATES = {"BASELINE_FORMING", "CALIBRATED_SHADOW", "ACTIVE_NOVELTY_RANKING"}


def canonical_signature(*, transition_grammar: Iterable[str], parent_context: str, closure_class: str) -> dict[str, Any]:
    grammar = tuple(str(item) for item in transition_grammar)
    payload = {
        "transition_grammar": list(grammar),
        "parent_context": str(parent_context),
        "closure_class": str(closure_class),
    }
    tokens = tuple(sorted({f"T:{item}" for item in grammar} | {f"P:{parent_context}", f"C:{closure_class}"}))
    return {
        "signature_id": f"PDSIG-{canonical_sha256(payload)[:32]}",
        "signature": payload,
        "tokens": list(tokens),
        "representation_version": NOVELTY_VERSION,
    }


def jaccard_distance(left_tokens: Iterable[str], right_tokens: Iterable[str]) -> float:
    left = set(left_tokens)
    right = set(right_tokens)
    union = left | right
    if not union:
        return 0.0
    return 1.0 - (len(left & right) / len(union))


def _percentile(value: float, population: list[float]) -> float | None:
    if not population:
        return None
    less_or_equal = sum(1 for item in population if item <= value)
    return less_or_equal / len(population)


@dataclass
class NoveltyBaseline:
    state: str = "BASELINE_FORMING"
    records: list[dict[str, Any]] = field(default_factory=list)
    eligible_days: set[str] = field(default_factory=set)
    market_conditions: set[str] = field(default_factory=set)
    unresolved_critical_incidents: int = 0
    shadow_evaluated_count: int = 0
    operator_disagreement_count: int = 0

    def __post_init__(self) -> None:
        if self.state not in NOVELTY_STATES:
            raise ValueError(f"unsupported novelty state: {self.state}")
        if self.state == "ACTIVE_NOVELTY_RANKING":
            raise PatternDiscoveryError("OPERATOR_GATE_REQUIRED: active novelty ranking is prohibited in PD-WP2")

    def readiness(self) -> dict[str, Any]:
        valid = len(self.records)
        controls = sum(1 for item in self.records if item.get("is_control"))
        checks = {
            "completed_valid_candidates": {"actual": valid, "required": 60, "pass": valid >= 60},
            "valid_controls": {"actual": controls, "required": 12, "pass": controls >= 12},
            "eligible_operating_days": {"actual": len(self.eligible_days), "required": 10, "pass": len(self.eligible_days) >= 10},
            "market_conditions": {"actual": len(self.market_conditions), "required": 2, "pass": len(self.market_conditions) > 1},
            "critical_incidents": {"actual": self.unresolved_critical_incidents, "required": 0, "pass": self.unresolved_critical_incidents == 0},
        }
        return {"checks": checks, "ready_for_calibrated_shadow": all(item["pass"] for item in checks.values())}

    def assess(self, signature: Mapping[str, Any]) -> dict[str, Any]:
        signature_id = str(signature.get("signature_id") or "")
        tokens = list(signature.get("tokens") or ())
        if not signature_id or not tokens:
            raise PatternDiscoveryError("novelty assessment requires a canonical provisional signature")
        same = [item for item in self.records if item["signature_id"] == signature_id]
        nearest = None
        distances: list[float] = []
        for item in self.records:
            distance = jaccard_distance(tokens, item["tokens"])
            distances.append(distance)
            nearest = distance if nearest is None else min(nearest, distance)
        last_occurrence = same[-1]["candidate_index"] if same else None
        assessment = {
            "assessment_id": f"PDNOV-{canonical_sha256({'signature_id': signature_id, 'population_size': len(self.records), 'state': self.state})[:32]}",
            "novelty_state": self.state,
            "signature_id": signature_id,
            "prior_signature_count": len(same),
            "prior_signature_frequency": 0.0 if not self.records else len(same) / len(self.records),
            "unseen_signature": len(same) == 0,
            "raw_nearest_neighbour_distance": nearest,
            "nearest_distance_percentile": _percentile(nearest, distances) if nearest is not None else None,
            "candidate_count_since_last_occurrence": None if last_occurrence is None else len(self.records) - 1 - last_occurrence,
            "badge": None,
            "badge_authority": "NONE",
            "queue_ranking_weight": 0.0,
            "independent_promotion_permitted": False,
            "hypothetical_rank_impact": None,
            "representation_version": NOVELTY_VERSION,
            "readiness": self.readiness(),
        }
        if self.state == "CALIBRATED_SHADOW":
            percentile = assessment["nearest_distance_percentile"]
            if percentile is None:
                band = "UNAVAILABLE"
            elif percentile >= 0.95:
                band = "HIGH"
            elif percentile >= 0.75:
                band = "MEDIUM"
            else:
                band = "LOW"
            assessment["badge"] = f"SHADOW_{band}"
            assessment["badge_authority"] = "SHADOW_ONLY"
            assessment["hypothetical_rank_impact"] = percentile
        return assessment

    def record(
        self,
        signature: Mapping[str, Any],
        *,
        candidate_id: str,
        eligible_day: str,
        market_condition: str,
        is_control: bool,
    ) -> dict[str, Any]:
        assessment = self.assess(signature)
        record = {
            "candidate_id": candidate_id,
            "candidate_index": len(self.records),
            "signature_id": signature["signature_id"],
            "tokens": list(signature["tokens"]),
            "eligible_day": eligible_day,
            "market_condition": market_condition,
            "is_control": bool(is_control),
            "assessment": assessment,
        }
        self.records.append(record)
        self.eligible_days.add(eligible_day)
        self.market_conditions.add(market_condition)
        if self.state == "CALIBRATED_SHADOW":
            self.shadow_evaluated_count += 1
        return record

    def enter_calibrated_shadow(self, *, calibration_transition_id: str) -> None:
        if self.state != "BASELINE_FORMING":
            raise PatternDiscoveryError("novelty baseline is not in BASELINE_FORMING")
        if not calibration_transition_id:
            raise PatternDiscoveryError("calibration transition record is required")
        if not self.readiness()["ready_for_calibrated_shadow"]:
            raise PatternDiscoveryError("NOVELTY_BASELINE_INSUFFICIENT")
        self.state = "CALIBRATED_SHADOW"

    def record_operator_disagreement(self) -> None:
        if self.state != "CALIBRATED_SHADOW":
            raise PatternDiscoveryError("operator disagreement metrics apply only in CALIBRATED_SHADOW")
        self.operator_disagreement_count += 1

    def activation_readiness(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "shadow_evaluated_count": self.shadow_evaluated_count,
            "required_shadow_evaluated_count": 20,
            "operator_disagreement_count": self.operator_disagreement_count,
            "operator_gate_required": True,
            "ready_to_propose_activation": self.state == "CALIBRATED_SHADOW" and self.shadow_evaluated_count >= 20,
            "active_authority": False,
        }

    def activate_ranking(self) -> None:
        raise PatternDiscoveryError("OPERATOR_GATE_REQUIRED: active novelty ranking is outside PD-WP2 authority")
