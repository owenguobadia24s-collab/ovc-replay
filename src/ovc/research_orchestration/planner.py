from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dag import CanonicalDag, DagError, build_canonical_dag
from .registry import RegistrySnapshot
from .serialization import logical_sha256


@dataclass(frozen=True)
class CanonicalPlan:
    profile_id: str
    profile_hash: str
    dag: CanonicalDag
    stage_spec_hashes: tuple[tuple[str, str], ...]
    external_input_types: tuple[str, ...] = ()

    @property
    def logical_hash(self) -> str:
        return logical_sha256({
            "profile_id": self.profile_id,
            "profile_hash": self.profile_hash,
            "dag_hash": self.dag.logical_hash,
            "stage_spec_hashes": [list(item) for item in self.stage_spec_hashes],
            "external_input_types": list(self.external_input_types),
        })

    @property
    def ordered_stage_ids(self) -> tuple[str, ...]:
        return self.dag.order

    def blocked_descendants(self, blocked_stage_ids: Iterable[str]) -> tuple[str, ...]:
        return self.dag.blocked_descendants(blocked_stage_ids)


def build_plan(*, snapshot: RegistrySnapshot, profile_id: str, external_input_types: Iterable[str] = ()) -> CanonicalPlan:
    profiles = snapshot.profile_by_id()
    if profile_id not in profiles:
        raise DagError("IROF_UNKNOWN_PROFILE", profile_id)
    profile = profiles[profile_id]
    stage_by_id = snapshot.stage_by_id()
    stage_specs = tuple(stage_by_id[stage_id] for stage_id in profile.included_stage_ids)
    dag = build_canonical_dag(stage_specs=snapshot.stage_specs, included_stage_ids=profile.included_stage_ids)
    external = tuple(sorted(set(str(item) for item in external_input_types)))

    for stage_id in dag.order:
        stage = stage_by_id[stage_id]
        parent_outputs: set[str] = set(external)
        declared_parent_ids = set(dag.parents_of(stage_id))
        for parent_id in declared_parent_ids:
            parent_outputs.update(stage_by_id[parent_id].output_types)
        missing_inputs = sorted(set(stage.input_types) - parent_outputs)
        if missing_inputs:
            raise DagError("IROF_INPUT_TYPE_UNSATISFIED", f"{stage_id}:{','.join(missing_inputs)}")

    hashes = tuple(sorted((stage_id, stage_by_id[stage_id].logical_hash) for stage_id in profile.included_stage_ids))
    return CanonicalPlan(
        profile_id=profile.profile_id,
        profile_hash=profile.logical_hash,
        dag=dag,
        stage_spec_hashes=hashes,
        external_input_types=external,
    )
