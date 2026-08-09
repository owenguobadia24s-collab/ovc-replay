from __future__ import annotations

from typing import Any, Mapping

from .models import PopulationSpec


def population_from_mapping(value: Mapping[str, Any]) -> PopulationSpec:
    return PopulationSpec(
        population_id=str(value["population_id"]),
        population_mode=str(value["population_mode"]),
        population_schema_version=str(value.get("population_schema_version", "0.1")),
        instrument=str(value["instrument"]),
        price_side=str(value["price_side"]),
        clock_lattice=str(value["clock_lattice"]),
        role=str(value["role"]),
        source_adapter_id=str(value["source_adapter_id"]),
        validation_access_state=str(value.get("validation_access_state", "LOCKED_UNCONSUMED")),
        capacity_tier=str(value.get("capacity_tier", "MICRO")),
        source_release_id=value.get("source_release_id"),
        source_manifest_hash=value.get("source_manifest_hash"),
        start_time=value.get("start_time"),
        end_time=value.get("end_time"),
        admissible_cutoff=value.get("admissible_cutoff"),
        expected_source_count=value.get("expected_source_count"),
        synthetic_fixture_id=value.get("synthetic_fixture_id"),
        generator_spec_id=value.get("generator_spec_id"),
        authority_binding_ids=tuple(value.get("authority_binding_ids", ())),
        external_artifact_root_alias=value.get("external_artifact_root_alias"),
    )


def population_identity_material(value: Mapping[str, Any] | PopulationSpec) -> dict[str, Any]:
    population = value if isinstance(value, PopulationSpec) else population_from_mapping(value)
    return population.semantic_dict()
