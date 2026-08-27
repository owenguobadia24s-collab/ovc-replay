from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from .core import (
    ResearchFreezeFrontier,
    SFFContractError,
    canonical_bytes,
    content_identity,
    require_first_valid_chronology,
)


@dataclass(frozen=True)
class StructuralAntecedent:
    antecedent_id: str
    owner_fact_id: str
    observed_at: datetime
    structural_type: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class TargetInstance:
    target_id: str
    antecedent_id: str
    grammar_identity: str
    ordinal: int
    structural_label: str


@dataclass(frozen=True)
class FrontierGeneration:
    generation_id: str
    freeze_frontier_id: str
    antecedent_id: str
    targets: tuple[TargetInstance, ...]
    source_mode: str = "SYNTHETIC_ONLY"


def _target_payload(
    antecedent: StructuralAntecedent,
    grammar_identity: str,
    ordinal: int,
    label: str,
) -> Mapping[str, Any]:
    return {
        "antecedent_id": antecedent.antecedent_id,
        "grammar_identity": grammar_identity,
        "ordinal": ordinal,
        "structural_label": label,
    }


def generate_one_step_frontier(
    *,
    antecedent: StructuralAntecedent,
    freeze: ResearchFreezeFrontier,
    grammar_identity: str,
    structural_labels: Sequence[str],
    expected_owner_fact_id: str,
) -> FrontierGeneration:
    if antecedent.owner_fact_id != expected_owner_fact_id:
        raise SFFContractError("ANTECEDENT_OWNER_BINDING_MISMATCH")
    require_first_valid_chronology(antecedent_at=antecedent.observed_at, cutoff_at=freeze.cutoff_at)
    if not grammar_identity or not structural_labels:
        raise SFFContractError("grammar and at least one target label are required")
    if len(set(structural_labels)) != len(structural_labels):
        raise SFFContractError("target labels must be unique within a generation")
    targets = tuple(
        TargetInstance(
            target_id=content_identity(
                "sff-target",
                _target_payload(antecedent, grammar_identity, ordinal, label),
            ),
            antecedent_id=antecedent.antecedent_id,
            grammar_identity=grammar_identity,
            ordinal=ordinal,
            structural_label=label,
        )
        for ordinal, label in enumerate(structural_labels)
    )
    identity_payload = {
        "freeze_frontier_id": freeze.frontier_id,
        "antecedent_id": antecedent.antecedent_id,
        "targets": targets,
        "source_mode": "SYNTHETIC_ONLY",
    }
    return FrontierGeneration(
        generation_id=content_identity("sff-frontier-generation", identity_payload),
        freeze_frontier_id=freeze.frontier_id,
        antecedent_id=antecedent.antecedent_id,
        targets=targets,
    )


def checkpoint(generation: FrontierGeneration) -> bytes:
    return canonical_bytes(generation)


def assert_replay_equivalent(left: FrontierGeneration, right: FrontierGeneration) -> None:
    if checkpoint(left) != checkpoint(right):
        raise SFFContractError("FRONTIER_REPLAY_MISMATCH")
