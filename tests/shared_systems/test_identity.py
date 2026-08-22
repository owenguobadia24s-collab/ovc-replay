from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.shared_systems.identity import (
    AmbiguousIdentityBinding,
    IdentityRegistry,
    LegacySerializationBinding,
    NonCanonicalIdentityPayload,
    ProfileCollisionError,
    SerializationProfile,
    UnknownIdentityBinding,
    canonicalize,
    load_registry,
    logical_identity,
)
from ovc.shared_systems.identity_comparator import canonical_bytes as comparator_bytes
from ovc.development.identity import canonical_json_bytes as development_canonical_bytes


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "registries" / "shared_systems" / "identity"
FIXTURE_ROOT = ROOT / "fixtures" / "shared_systems" / "identity"
PROFILE_ID = "SHSI.SERIALIZATION.CANONICAL_JSON_NFC.v1"
PROJECTION_ID = "SHSI.IDENTITY.FIXTURE.v1"


def registry() -> IdentityRegistry:
    return load_registry(REGISTRY_ROOT)


def test_registry_keeps_hash_profile_projection_identifiers_independent() -> None:
    loaded = registry()
    profile = loaded.profile(PROFILE_ID)
    assert profile.hash_algorithm_ref == "SHA-256"
    assert profile.serialization_profile_id != profile.hash_algorithm_ref
    assert profile.identity_projection_ref != profile.hash_algorithm_ref
    assert loaded.profile("OVC.DEVELOPMENT.CANONICAL_JSON.v1").hash_algorithm_ref == "SHA-256"


def test_contract_schemas_validate_frozen_registry_entries() -> None:
    bindings = (
        ("serialization_profile_v0_1.schema.json", "SERIALIZATION_PROFILE_REGISTRY_v0_1.json"),
        ("identity_projection_v0_1.schema.json", "IDENTITY_PROJECTION_REGISTRY_v0_1.json"),
        ("legacy_serialization_binding_v0_1.schema.json", "LEGACY_SERIALIZATION_BINDING_REGISTRY_v0_1.json"),
    )
    for schema_name, registry_name in bindings:
        schema = json.loads((ROOT / "schemas" / "shared_systems" / schema_name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        rows = json.loads((REGISTRY_ROOT / registry_name).read_text(encoding="utf-8"))["entries"]
        for row in rows:
            assert set(row) == set(schema["required"])


def test_golden_vectors_match_reference_and_independent_comparator() -> None:
    loaded = registry()
    profile = loaded.profile(PROFILE_ID)
    projection = loaded.projection(PROJECTION_ID)
    fixture = json.loads((FIXTURE_ROOT / "SHSI_IDENTITY_GOLDEN_VECTORS_v0_1.json").read_text(encoding="utf-8"))
    for vector in fixture["vectors"]:
        projected = projection.project(vector["input"])
        reference = canonicalize(projected, profile)
        assert reference.decode("utf-8") == vector["expected_utf8"]
        assert reference == comparator_bytes(projected)
        assert hashlib.sha256(reference).hexdigest() == vector["expected_sha256"]


def test_existing_development_primitive_is_reused_as_equivalence_baseline() -> None:
    loaded = registry()
    profile = loaded.profile(PROFILE_ID)
    value = {"a": [1, True, None, "NFC café"], "z": {"x": 12.5}}
    assert canonicalize(value, profile) == development_canonical_bytes(value)


def test_identity_is_stable_across_clean_hash_seed_processes() -> None:
    script = (
        "from pathlib import Path;"
        "from ovc.shared_systems.identity import load_registry,logical_identity;"
        f"r=load_registry(Path({str(REGISTRY_ROOT)!r}));"
        f"print(logical_identity({{'version':1,'payload':{{'z':2,'a':1}},'kind':'fixture'}},"
        f"serialization_profile_id={PROFILE_ID!r},identity_projection_id={PROJECTION_ID!r},registry=r)['logical_digest'])"
    )
    observed = []
    for seed in ("1", "872341"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        observed.append(subprocess.check_output([sys.executable, "-c", script], cwd=ROOT, env=env, text=True).strip())
    assert len(set(observed)) == 1


def test_material_profile_change_changes_bound_logical_identity() -> None:
    loaded = registry()
    value = {"kind": "fixture", "payload": {"a": 1}}
    first = logical_identity(value, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    other = loaded.profile("OVC.DEVELOPMENT.CANONICAL_JSON.v1")
    second = logical_identity(value, serialization_profile_id=other.serialization_profile_id, identity_projection_id=PROJECTION_ID, registry=loaded)
    assert first["canonical_content_digest"] == second["canonical_content_digest"]
    assert first["logical_digest"] != second["logical_digest"]
    assert first["physical_blob_digest"] != second["physical_blob_digest"]


def test_profile_collision_fixture_fails_closed() -> None:
    loaded = registry()
    fixture = json.loads((FIXTURE_ROOT / "SHSI_PROFILE_COLLISION_FIXTURE_v0_1.json").read_text(encoding="utf-8"))
    profiles = [SerializationProfile.from_mapping(row) for row in fixture["profiles"]]
    with pytest.raises(ProfileCollisionError, match="SERIALIZATION_PROFILE_COLLISION"):
        IdentityRegistry(algorithms=loaded.algorithms.values(), profiles=profiles, projections=loaded.projections.values())


def test_unknown_profile_and_noncanonical_inputs_fail_closed() -> None:
    loaded = registry()
    with pytest.raises(UnknownIdentityBinding, match="SERIALIZATION_PROFILE_UNKNOWN"):
        loaded.profile("SHA-256")
    with pytest.raises(NonCanonicalIdentityPayload, match="NEGATIVE_ZERO_REJECTED"):
        logical_identity({"kind": "fixture", "payload": -0.0}, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    with pytest.raises(NonCanonicalIdentityPayload, match="UNICODE_NOT_NFC"):
        logical_identity({"kind": "cafe\u0301", "payload": 1}, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    with pytest.raises(NonCanonicalIdentityPayload, match="IDENTITY_REQUIRED_FIELDS_MISSING"):
        logical_identity({"kind": "fixture"}, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    with pytest.raises(NonCanonicalIdentityPayload, match="IDENTITY_FIELD_ROLE_UNDECLARED"):
        logical_identity({"kind": "fixture", "payload": 1, "undeclared": "cannot disappear"}, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)


def test_projection_excludes_self_machine_and_descriptive_fields() -> None:
    loaded = registry()
    value = {
        "kind": "fixture", "payload": {"a": 1}, "id": "self", "description": "display",
        "hostname": "worker-a", "path": "C:/machine/local", "pid": 42,
    }
    with_noise = logical_identity(value, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    clean = logical_identity({"kind": "fixture", "payload": {"a": 1}}, serialization_profile_id=PROFILE_ID, identity_projection_id=PROJECTION_ID, registry=loaded)
    assert with_noise["logical_digest"] == clean["logical_digest"]


def test_legacy_resolution_returns_stored_digest_without_rehash() -> None:
    loaded = registry()
    binding = loaded.resolve_legacy(
        "SHSI.FIXTURE.LEGACY.001",
        owner_namespace="OVC-SHARED-SYSTEMS-v0.1",
        pack_id="SHSI-WP1-FIXTURES",
        generation_id="legacy-generation-001",
    )
    assert binding.historical_digest == "4d600b796a7f8ec2d1b592ca21f077f7cc09f8bba2366394551c73afadf13f8f"
    with pytest.raises(UnknownIdentityBinding, match="LEGACY_IDENTITY_BINDING_UNKNOWN"):
        loaded.resolve_legacy("SHSI.FIXTURE.LEGACY.001", owner_namespace="wrong", pack_id="SHSI-WP1-FIXTURES", generation_id="legacy-generation-001")


def test_ambiguous_legacy_context_fails_closed() -> None:
    loaded = registry()
    original = loaded.legacy_bindings[0]
    duplicate_context = replace(original, binding_id="SHSI.LEGACY_BINDING.FIXTURE.002")
    ambiguous = IdentityRegistry(
        algorithms=loaded.algorithms.values(), profiles=loaded.profiles.values(),
        projections=loaded.projections.values(), legacy_bindings=(original, duplicate_context),
    )
    with pytest.raises(AmbiguousIdentityBinding, match="LEGACY_IDENTITY_BINDING_AMBIGUOUS"):
        ambiguous.resolve_legacy(original.legacy_identifier, owner_namespace=original.owner_namespace, pack_id=original.pack_id, generation_id=original.generation_id)


def test_reference_identity_core_preserves_stage0_bootstrap_boundary() -> None:
    source = (ROOT / "src" / "ovc" / "shared_systems" / "identity.py").read_text(encoding="utf-8")
    assert "ovc.development" not in source
    assert "ovc.research_operations" not in source
    assert "shared_systems.resolution" not in source
