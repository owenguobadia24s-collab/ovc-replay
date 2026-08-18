from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import validate_vit_lineage_record


@dataclass(frozen=True)
class OpenVitPlacement:
    """One open permanent-PR VIT placement available to the physical gateway."""

    pr_number: int
    head_sha: str
    lineage_record: Mapping[str, Any]


@dataclass(frozen=True)
class VitTrainPredecessor:
    """The exact unresolved VIT placement whose result tree is this placement's predecessor."""

    pr_number: int
    head_sha: str
    generation_id: str
    placement_id: str
    train_generation_id: str
    ordinal: int
    result_tree: str


def _tree(value: object, label: str) -> str:
    tree = str(value or "")
    if len(tree) != 40:
        raise VitContractError(f"{label}_INVALID")
    try:
        int(tree, 16)
    except ValueError as exc:
        raise VitContractError(f"{label}_INVALID") from exc
    if tree.lower() != tree:
        raise VitContractError(f"{label}_INVALID")
    return tree


def _generation(record: Mapping[str, Any]) -> Mapping[str, Any]:
    generation = record.get("generation")
    if not isinstance(generation, Mapping):
        raise VitContractError("VIT_LINEAGE_GENERATION_INVALID")
    return generation


def resolve_vit_train_predecessor(
    *,
    current_lineage_record: Mapping[str, Any],
    current_main_tree: str,
    open_placements: Sequence[OpenVitPlacement],
) -> VitTrainPredecessor | None:
    """Resolve only a predecessor encoded by the current VIT placement.

    PR creation order is deliberately absent from this decision.  The current
    placement names its exact predecessor *tree*.  If that tree is already
    physical there is no unresolved predecessor and unrelated open PRs cannot
    hold the physical lease.  Otherwise an open VIT placement can be the
    predecessor only when its exact result tree equals the current placement's
    predecessor tree.  A same-train lower ordinal is additionally enforced when
    both placements share one train generation.

    A missing or ambiguous exact-tree predecessor fails closed so physical main
    can never be advanced by guessing from PR number, recency, title or queue
    position.
    """

    current = validate_vit_lineage_record(current_lineage_record)
    current_generation = _generation(current_lineage_record)
    current_predecessor = current_generation.get("predecessor_tree")
    if not isinstance(current_predecessor, Mapping):
        raise VitContractError("VIT_LINEAGE_PREDECESSOR_TREE_INVALID")
    expected_tree = _tree(current_predecessor.get("tree_sha"), "VIT_PREDECESSOR_TREE")
    main_tree = _tree(current_main_tree, "VIT_CURRENT_MAIN_TREE")

    if main_tree == expected_tree:
        return None

    current_train = str(current_generation.get("train_generation_id", "")).strip()
    current_ordinal = int(current_generation.get("ordinal", -1))
    matches: list[VitTrainPredecessor] = []

    for candidate in open_placements:
        candidate_lineage = validate_vit_lineage_record(candidate.lineage_record)
        if candidate_lineage.generation_id == current.generation_id:
            continue
        candidate_generation = _generation(candidate.lineage_record)
        candidate_result = candidate_generation.get("result_tree")
        if not isinstance(candidate_result, Mapping):
            raise VitContractError("VIT_LINEAGE_RESULT_TREE_INVALID")
        result_tree = _tree(candidate_result.get("tree_sha"), "VIT_CANDIDATE_RESULT_TREE")
        if result_tree != expected_tree:
            continue

        candidate_train = str(candidate_generation.get("train_generation_id", "")).strip()
        candidate_ordinal = int(candidate_generation.get("ordinal", -1))
        if candidate_train == current_train and candidate_ordinal >= current_ordinal:
            raise VitContractError("VIT_TRAIN_PREDECESSOR_ORDINAL_INVALID")

        matches.append(
            VitTrainPredecessor(
                pr_number=int(candidate.pr_number),
                head_sha=str(candidate.head_sha),
                generation_id=candidate_lineage.generation_id,
                placement_id=candidate_lineage.placement_id,
                train_generation_id=candidate_train,
                ordinal=candidate_ordinal,
                result_tree=result_tree,
            )
        )

    if len(matches) > 1:
        raise VitContractError("VIT_TRAIN_PREDECESSOR_AMBIGUOUS")
    if not matches:
        raise VitContractError("VIT_PLACEMENT_PREDECESSOR_NOT_PHYSICAL")
    return matches[0]
