from __future__ import annotations

from pathlib import Path

from ovc.opt_b.c2p_v0_2.rs0_source_locator_recovery import inspect_repository_source_chain


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_recovery_finds_current_authority_and_exact_c1_upstream_but_not_current_materialisation() -> None:
    result = inspect_repository_source_chain(_repo_root())
    assert result["current_c2"]["package_id"] == "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
    assert result["current_c2e"]["boundary_pack_id"] == "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
    assert result["upstream_c1"]["release_id"] == "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2"
    assert result["upstream_c1"]["remote_object_count"] > 0
    assert result["current_c2"]["materialised_2021_2023_locator"] == "NOT_PRESENT_IN_REPOSITORY_RECORDS"
    assert result["current_c2e"]["materialised_2021_2023_locator"] == "NOT_PRESENT_IN_REPOSITORY_RECORDS"
    assert result["recovery_status"] == "BLOCKED_CURRENT_C2_VNEXT_C2E_2021_2023_MATERIALISATION_ABSENT"


def test_recovery_rejects_historical_c2_v2_as_new_evidence_parent() -> None:
    result = inspect_repository_source_chain(_repo_root())
    assert result["legacy_c2"]["remote_verified"] is True
    assert result["legacy_c2"]["remote_prefix"].startswith("ovc-evidence/canonical/releases/OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2/")
    assert result["legacy_c2"]["disposition"] == "REJECT_AS_NEW_EVIDENCE_PARENT_LEGACY_READ_ONLY_ONLY"
    assert result["fallback_forbidden"] is True
    assert result["run_authority_consumed"] is False


def test_historical_c2_vnext_replay_is_not_misclassified_as_2021_2023_source() -> None:
    result = inspect_repository_source_chain(_repo_root())
    replay = result["historical_c2_vnext_replay"]
    assert replay["google_drive_replay_folder_id"]
    assert replay["logical_population_sha256"]
    assert replay["scope"] == "HISTORICAL_JUNE_REPLAY_ONLY_NOT_2021_2023_SOURCE"
