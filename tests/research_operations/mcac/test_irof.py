from __future__ import annotations

from ovc.research_operations.mcac.irof import mcac_authority_registry, mcac_pipeline_profile, mcac_stage_specs, preflight_source_use


def test_stage_pack_is_deterministic_inactive_and_checkpointed():
    stages = mcac_stage_specs()
    assert [stage.stage_id for stage in stages] == ["MCAC_ALIGNMENT", "MCAC_CORRESPONDENCE"]
    assert all(stage.deterministic_mode == "EXACT" and stage.checkpoint_capability == "STAGE" for stage in stages)
    assert mcac_pipeline_profile().authority_policy_ref == "MCAC_EXISTING_OWNER_OR_SYNTHETIC_AUTHORITY_ONLY"
    assert set(mcac_authority_registry().ids()) == {"AUTH.LSIAC.MCAC.INACTIVE.CONFORMANCE.v0.1", "AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1"}


def test_source_use_preflight_denies_before_protected_resolution():
    assert preflight_source_use("SYNTHETIC_CONFORMANCE") == "READY"
    assert preflight_source_use("SEALED_CONSUMED_REFERENCE") == "NOT_AUTHORISED"
    assert preflight_source_use("SEALED_CONSUMED_REFERENCE", reference_authority_effective=True) == "READY"
    assert preflight_source_use("OWNER_PUBLISHED_DERIVED_RECORDS") == "NOT_AUTHORISED"
    assert preflight_source_use("OWNER_PUBLISHED_DERIVED_RECORDS", owner_authority_effective=True) == "READY"
    assert preflight_source_use("LOCATOR_ONLY") == "NOT_AUTHORISED"
    assert preflight_source_use("FORBIDDEN") == "NOT_AUTHORISED"
