from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from ovc.shared_systems.envelopes import AdapterDescriptor, CompatibilityContract
from ovc.shared_systems.resolution import (
    AdapterRegistry,
    CompatibilityRegistry,
    MigrationInventory,
    NonMigrationDecision,
    NonMigrationDecisionRegistry,
    RegistryDirectory,
    RegistryDirectoryEntry,
    ResolutionRequest,
    ServiceConsumptionBinding,
    ServiceCurrentBinding,
    SharedExecutionContext,
    SharedResolutionError,
    SharedServiceDescriptor,
    resolve_exact,
)


ENTRY = RegistryDirectoryEntry("SVC.1", "OWNER.1", "REGISTRY.1", "STAGE0.1")


def directory(*entries: RegistryDirectoryEntry) -> RegistryDirectory:
    return RegistryDirectory(
        entries or (ENTRY,), stage0_owner_bindings={"SVC.1": "OWNER.1"}
    )


def descriptor(**changes: object) -> SharedServiceDescriptor:
    values = {
        "service_id": "SVC.1",
        "release_id": "SVC.1.RELEASE.1",
        "owner_programme_id": "OWNER.1",
        "registry_id": "REGISTRY.1",
        "capability_ids": ("CAP.1",),
        "contract_refs": ("CONTRACT.PRODUCER.1",),
        "qualification_ref": "QUAL.1",
        "lifecycle": "CURRENT",
        "materialized": True,
    }
    values.update(changes)
    return SharedServiceDescriptor(**values)


def request(**changes: object) -> ResolutionRequest:
    values = {
        "request_id": "REQUEST.1",
        "requester_programme_id": "CONSUMER.1",
        "requester_generation": "CONSUMER.1.GEN.1",
        "service_id": "SVC.1",
        "capability_id": "CAP.1",
        "required_release_id": "SVC.1.RELEASE.1",
        "required_contract_ref": "CONTRACT.CONSUMER.1",
        "semantic_scope": "SCOPE.1",
        "authority_ref": "AUTH.1",
        "environment_ref": "ENV.1",
        "cutoff_ref": "CUTOFF.1",
    }
    values.update(changes)
    return ResolutionRequest(**values)


def binding(**changes: object) -> ServiceConsumptionBinding:
    values = {
        "binding_id": "CONSUME.1",
        "consumer_programme_id": "CONSUMER.1",
        "service_id": "SVC.1",
        "capability_id": "CAP.1",
        "allowed_release_ids": ("SVC.1.RELEASE.1",),
        "authority_refs": ("AUTH.1",),
    }
    values.update(changes)
    return ServiceConsumptionBinding(**values)


COMPATIBILITY = CompatibilityContract(
    "COMPAT.1",
    "CONTRACT.PRODUCER.1",
    "CONTRACT.CONSUMER.1",
    "ADAPTER_REQUIRED",
    "SCOPE.1",
    ("EXACT_FIELDS",),
)
ADAPTER = AdapterDescriptor(
    "ADAPTER.1",
    "OWNER.1",
    "CONTRACT.PRODUCER.1",
    "CONTRACT.CONSUMER.1",
    (("value", "value"),),
    (),
)


def resolve(**changes: object):
    args = {
        "request": request(),
        "directory": directory(),
        "owner_descriptors": {"REGISTRY.1": (descriptor(),)},
        "consumption_bindings": (binding(),),
        "qualification_currentness": {"QUAL.1": "CURRENT"},
        "compatibility_registry": CompatibilityRegistry((COMPATIBILITY,)),
        "adapter_registry": AdapterRegistry((ADAPTER,)),
    }
    args.update(changes)
    req = args.pop("request")
    return resolve_exact(req, **args)


def test_exact_resolution_golden_is_fully_bound() -> None:
    manifest = resolve()
    assert manifest.status == "RESOLVED"
    assert manifest.release_id == "SVC.1.RELEASE.1"
    assert manifest.registry_id == "REGISTRY.1"
    assert manifest.compatibility_ref == "COMPAT.1"
    assert manifest.adapter_chain == ("ADAPTER.1",)
    assert manifest.qualification_ref == "QUAL.1"
    assert manifest.consumption_binding_ref == "CONSUME.1"
    assert manifest.authority_effect == "NONE" and manifest.logical_id


def test_normative_latest_is_forbidden_in_every_exact_request_plane() -> None:
    with pytest.raises(SharedResolutionError, match="LATEST"):
        request(required_release_id="latest")
    with pytest.raises(SharedResolutionError, match="LATEST"):
        descriptor(release_id="SVC.latest")
    with pytest.raises(SharedResolutionError, match="LATEST"):
        ServiceCurrentBinding("B", "SVC.1", "latest")


def test_directory_cannot_override_or_ambiguate_stage0_owner() -> None:
    with pytest.raises(SharedResolutionError, match="GOVERNANCE_CONFLICT"):
        directory(replace(ENTRY, owner_programme_id="OTHER"))
    with pytest.raises(SharedResolutionError, match="DIRECTORY_AMBIGUOUS"):
        directory(ENTRY, ENTRY)


def test_missing_directory_registry_and_release_are_typed() -> None:
    assert resolve(directory=directory()) .status == "RESOLVED"
    missing_directory = RegistryDirectory(
        (), stage0_owner_bindings={"SVC.1": "OWNER.1"}
    )
    assert resolve(directory=missing_directory).reason_codes == ("DIRECTORY_ENTRY_MISSING",)
    assert resolve(owner_descriptors={}).reason_codes == ("OWNER_REGISTRY_MISSING",)
    assert resolve(owner_descriptors={"REGISTRY.1": ()}).reason_codes == (
        "EXACT_RELEASE_MISSING",
    )


def test_ambiguous_exact_release_fails_closed() -> None:
    manifest = resolve(
        owner_descriptors={"REGISTRY.1": (descriptor(), descriptor())}
    )
    assert manifest.status == "AMBIGUOUS"
    assert manifest.reason_codes == ("EXACT_RELEASE_AMBIGUOUS",)


def test_stale_qualification_fails_closed() -> None:
    manifest = resolve(qualification_currentness={"QUAL.1": "STALE"})
    assert manifest.status == "STALE_QUALIFICATION"


def test_missing_or_wrong_authority_binding_fails_closed() -> None:
    assert resolve(consumption_bindings=()).status == "UNAUTHORIZED"
    assert resolve(request=request(authority_ref="AUTH.2")).reason_codes == (
        "AUTHORITY_REF_NOT_BOUND",
    )


def test_incompatible_or_missing_adapter_fails_closed() -> None:
    incompatible = replace(COMPATIBILITY, compatibility_class="INCOMPATIBLE")
    assert resolve(
        compatibility_registry=CompatibilityRegistry((incompatible,))
    ).status == "INCOMPATIBLE"
    assert resolve(adapter_registry=AdapterRegistry(())).reason_codes == (
        "REQUIRED_ADAPTER_MISSING",
    )


def test_direct_contract_match_wins_without_adapter_or_registry_guessing() -> None:
    direct = descriptor(
        contract_refs=("CONTRACT.OTHER.1", "CONTRACT.CONSUMER.1")
    )
    manifest = resolve(
        owner_descriptors={"REGISTRY.1": (direct,)},
        compatibility_registry=CompatibilityRegistry(()),
        adapter_registry=AdapterRegistry(()),
    )
    assert manifest.status == "RESOLVED"
    assert manifest.contract_ref == "CONTRACT.CONSUMER.1"
    assert manifest.compatibility_ref is None and manifest.adapter_chain == ()


def test_multiple_compatible_contract_paths_are_ambiguous() -> None:
    second = CompatibilityContract(
        "COMPAT.2",
        "CONTRACT.PRODUCER.2",
        "CONTRACT.CONSUMER.1",
        "BACKWARD_COMPATIBLE",
        "SCOPE.1",
        ("EXACT_FIELDS",),
    )
    manifest = resolve(
        owner_descriptors={
            "REGISTRY.1": (
                descriptor(
                    contract_refs=("CONTRACT.PRODUCER.1", "CONTRACT.PRODUCER.2")
                ),
            )
        },
        compatibility_registry=CompatibilityRegistry((COMPATIBILITY, second)),
    )
    assert manifest.status == "AMBIGUOUS"
    assert manifest.reason_codes == ("CONTRACT_PATH_AMBIGUOUS",)


def test_owner_conflict_and_unmaterialized_release_fail_closed() -> None:
    conflict = descriptor(owner_programme_id="OTHER")
    assert resolve(owner_descriptors={"REGISTRY.1": (conflict,)}).status == (
        "OWNER_CONFLICT"
    )
    assert resolve(
        owner_descriptors={"REGISTRY.1": (descriptor(materialized=False),)}
    ).status == "NOT_MATERIALIZED"


def test_context_is_frozen_until_explicit_reresolution_barrier() -> None:
    original = resolve()
    context = SharedExecutionContext.freeze("CTX.1", original)
    replacement = resolve(
        request=request(request_id="REQUEST.2", required_release_id="SVC.1.RELEASE.2"),
        owner_descriptors={
            "REGISTRY.1": (descriptor(release_id="SVC.1.RELEASE.2"),)
        },
        consumption_bindings=(
            binding(allowed_release_ids=("SVC.1.RELEASE.2",)),
        ),
    )
    assert context.release_id == "SVC.1.RELEASE.1"
    moved = context.reresolve(replacement, barrier_ref="BARRIER.1")
    assert moved.release_id == "SVC.1.RELEASE.2"
    assert moved.reresolution_barrier_ref == "BARRIER.1"


def test_current_bindings_cannot_activate_a_consumer_or_service() -> None:
    assert binding().status == "INACTIVE_REFERENCE"
    with pytest.raises(SharedResolutionError, match="ACTIVE_CONSUMER"):
        binding(status="ACTIVE")
    with pytest.raises(SharedResolutionError, match="ACTIVE_SERVICE"):
        ServiceCurrentBinding("B", "SVC.1", "SVC.1.RELEASE.1", status="ACTIVE")


def test_nonmigration_decisions_trigger_without_migrating() -> None:
    inventory = MigrationInventory(
        "INV.1", "CONSUMER.1", "LEGACY.BINDING.1", "SVC.1", "DO_NOT_MIGRATE"
    )
    decision = NonMigrationDecision(
        "NMD.1",
        inventory.consumer_programme_id,
        inventory.current_binding_ref,
        ("OWNER_LOCAL_PATH_CONFORMANT",),
        ("CONTRACT.CHANGE", "QUALIFICATION.STALE"),
        "REVIEW.BARRIER.1",
    )
    registry = NonMigrationDecisionRegistry((decision,))
    assert registry.triggered(("UNRELATED",)) == ()
    assert registry.triggered(("QUALIFICATION.STALE",)) == ("NMD.1",)
    projection = registry.projection()
    assert projection["authority_effect"] == "NONE" and projection["logical_id"]
    assert inventory.authority_effect == "NONE"


def test_wp5_schema_and_synthetic_fixture_are_valid_and_nonmutating() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "schemas/shared_systems/exact_resolution_migration_v0_1.schema.json").read_text()
    )
    fixture = json.loads(
        (root / "fixtures/shared_systems/resolution/SHSI_WP5_SYNTHETIC_RESOLUTION_FIXTURES_v0_1.json").read_text()
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["$defs"]["SharedServiceDescriptor"]["required"]) <= set(
        fixture["descriptor"]
    )
    assert set(schema["$defs"]["ResolutionRequest"]["required"]) <= set(
        fixture["request"]
    )
    assert fixture["authority_effect"] == "NONE"
    assert fixture["consumer_changes"] == []
    assert {item["status"] for item in fixture["failure_envelopes"]} >= {
        "MISSING",
        "AMBIGUOUS",
        "STALE_QUALIFICATION",
        "INCOMPATIBLE",
        "UNAUTHORIZED",
        "OWNER_CONFLICT",
    }
