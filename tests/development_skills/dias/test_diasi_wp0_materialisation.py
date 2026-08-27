from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
PLAN_IDENTITY = ROOT / "docs/plans/dias-v0-1/DIASI_PLAN_SOURCE_IDENTITY_v0_1_R1.json"
WP0 = ROOT / "docs/programmes/dias-v0-1/wp0"
STATE_ROOT = ROOT / "registries/implementation/dias_v0_1"
PG_MIGRATION_REGISTRY = ROOT / "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"
PGN_CENSUS_BUILDER = ROOT / "scripts/governance/build_pgn_wp2_census.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"4e7401a4b7a91d77fe862fec24317035a46eb6ca:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_exact_governing_source_identities() -> None:
    identity = load(PLAN_IDENTITY)
    assert identity["programme_id"] == "OVC-DIAS-CONFORMANCE-v0.1"
    assert identity["plan_id"] == "OVC-DIAS-CONFORMANCE-PLAN-0.1-R1"
    observed = {source["role"]: (source["sha256"], source["byte_size"]) for source in identity["sources"]}
    assert observed == {
        "CONFORMANCE_PLAN": ("cf5aba8e17fce178a24e96088e2e998f64ff70499170da6ae8bfda793586ab6e", 76952),
        "DGS_GOVERNING_DESIGN": ("993f829a45bb0ead0f32ebdd4b73688585b5863bba95000e871fe4222490f088", 85275),
        "RACPR_GOVERNING_DESIGN": ("71e6cfd32e462d700c85b77d81f333d19eed9b441c1bf229661159cd40d66279", 60615),
        "INDEPENDENT_ADVERSARIAL_PRESSURE_TEST": ("c763172a3b49e4abdfef6a9811bcbc2b0d20fb42561e22071c3f9eae5ccadde0", 51755),
    }


def test_g0_phrase_and_reserved_authority_are_exact() -> None:
    decision = load(WP0 / "DIASI_G0_OPERATOR_DECISION.json")
    assert decision["operator_phrase"] == "OVC APPROVE DIASI-G0 PASS"
    assert decision["decision"] == "PASS"
    assert decision["next_reserved_operator_gate"] == "DIASI-G-DGS-CUTOVER-DRAIN"
    denied = set(decision["authority_after_materialisation"]["denied"])
    assert {"LIVE_CUTOVER", "CERS_OR_PES_REMOVAL", "PROOF_SUBSTITUTION", "RULESET_MUTATION"} <= denied


def test_protection_manifest_binds_exact_main_and_one_writer() -> None:
    manifest = load(WP0 / "DIASI_WP0_REPOSITORY_PROTECTION_MANIFEST.json")
    assert manifest["physical_main"] == {
        "commit": "4e7401a4b7a91d77fe862fec24317035a46eb6ca",
        "tree": "9b5a2ef28be73bc6c575063571fbee47d3501052",
    }
    assert manifest["ruleset"]["id"] == 20229411
    assert manifest["ruleset"]["bypass_actors"] == []
    assert manifest["physical_writer"]["controller"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert manifest["physical_writer"]["parallel_physical_merge"] is False


def test_owner_sources_and_historical_corpus_bind_baseline_blobs() -> None:
    owners = load(WP0 / "DIASI_WP0_OWNER_CURRENTNESS_BASELINE.json")
    for owner in owners["owners"]:
        if "pointer_blob" in owner:
            assert git_blob(owner["pointer"]) == owner["pointer_blob"]
        if owner.get("state_blob"):
            assert git_blob(owner["state"]) == owner["state_blob"]
    corpus = load(WP0 / "DIASI_WP0_HISTORICAL_REPLAY_CORPUS_MANIFEST.json")
    for member in corpus["members"]:
        assert git_blob(member["path"]) == member["blob"]


def test_universe_and_pilot_were_frozen_without_live_authority() -> None:
    universe = load(WP0 / "DIASI_WP0_QUALIFICATION_UNIVERSE_MANIFEST.json")
    pilot = load(WP0 / "DIASI_WP0_PILOT_CLASS_SELECTION_MANIFEST.json")
    assert universe["frozen_before_diasi_shadow_outcomes"] is True
    assert len(universe["required_adversarial_cases"]) == 16
    assert universe["outcomes_at_freeze"] == "UNOBSERVED"
    assert pilot["selected_candidate"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert pilot["live_use_authority"] == "DENIED_PENDING_DIASI-G-DGS-CUTOVER-DRAIN"
    assert pilot["proof_substitution"] is False


def test_vit_authority_and_frontier_identities_are_canonical() -> None:
    authority = load(WP0 / "DIASI_WP0_VIT_AUTHORITY_MANIFEST.json")
    frontier = load(WP0 / "DIASI_WP0_VIT_DEPENDENCY_FRONTIER.json")
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert authority["payload"]["authority_class"] == "AUTO_EXECUTABLE"
    assert frontier["payload"]["predecessor_requirement"] == "PHYSICAL_MATERIALISATION_REQUIRED"


def test_retirement_census_is_complete_but_not_authority() -> None:
    matrix = load(WP0 / "DIASI_WP0_RETIREMENT_COVERAGE_MATRIX.json")
    census = load(WP0 / "DIASI_WP0_CERS_PES_CENSUS.json")
    assert matrix["census_complete_for_wp0"] is True
    assert matrix["retirement_eligible"] is False
    assert len(matrix["functions"]) == 7
    assert len(census["cers"]["admitted_programmes"]) == 5
    assert census["retirement_authority"] == "DENIED"


def test_machine_state_is_fail_closed_and_dgs_is_decoupled() -> None:
    state = load(STATE_ROOT / "DIASI_CURRENT_v0_2.json")
    assert state["current_gate"] in {"DIASI-G0", "DIASI-G2-ALGORITHMIC"}
    if state["current_gate"] == "DIASI-G2-ALGORITHMIC":
        assert "DIASI-WP0" in state["completed_packets"]
        assert state["algorithmic_gate"] == "PASS"
    assert state["dgs_independent_of_racpr"] is True
    assert state["racpr_disposition"].startswith("REFERENCE_ONLY")
    assert state["live_cutover"] is False
    assert state["retirement"] is False
    assert state["proof_substitution"] is False


def test_diasi_state_is_not_a_programme_genesis_legacy_migration_target() -> None:
    path = "registries/implementation/dias_v0_1/DIASI_PROGRAMME_STATE_v0_1.json"
    registry = load(PG_MIGRATION_REGISTRY)
    assert path in registry["discovery"]["exclude_paths"]
    assert "OVC-DIAS-CONFORMANCE-v0.1" in registry["discovery"]["native_programmes_excluded"]
    assert path in PGN_CENSUS_BUILDER.read_text(encoding="utf-8")


def test_all_wp0_json_is_canonicalizable() -> None:
    paths = sorted(WP0.glob("*.json")) + sorted(STATE_ROOT.glob("*.json")) + [PLAN_IDENTITY]
    assert paths
    for path in paths:
        value = load(path)
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        assert len(hashlib.sha256(canonical).hexdigest()) == 64
