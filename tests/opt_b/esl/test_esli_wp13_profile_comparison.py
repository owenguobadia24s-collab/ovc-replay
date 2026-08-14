from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/releases/optb-esl-conformance-v0-1/esli-wp13/evidence"
MANIFEST = ROOT / "registries/opt_b/esl/JuneProfileComparisonManifest_v2.json"
RUNNER = ROOT / "src/ovc/opt_b/esl/profile_comparison.py"


def load(name: str):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_wp13_manifest_is_pre_result_frozen_and_no_winner():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["freeze_state"] == "FROZEN_BEFORE_PROFILE_RESULT_INSPECTION"
    assert manifest["profiles"] == ["BASE_STRUCTURAL", "ORGANISATION_ENRICHED", "CONSTRAINT_ENRICHED", "FULL_RESEARCH"]
    assert manifest["winner_synthesis"] == "FORBIDDEN"
    assert manifest["authority_effect"] == "NONE"
    assert manifest["profile_bindings"]["CONSTRAINT_ENRICHED"]["predeclared_comparator_pack"] == "NONE_MATERIALIZED_AT_FREEZE"


def test_wp13_runner_identity_matches_frozen_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest() == manifest["profile_bindings"]["BASE_STRUCTURAL"]["runner_sha256"]


def test_wp13_information_profiles_are_fail_honest_and_non_promotional():
    ledger = load("ProfileInformationLedger_v1.json")
    entries = {row["profile"]: row for row in ledger["entries"]}
    assert ledger["winner_synthesis"] == "FORBIDDEN"
    assert ledger["authority_effect"] == "NONE"
    assert entries["BASE_STRUCTURAL"]["common_population"]["eligible_record_count"] == 2036
    assert entries["BASE_STRUCTURAL"]["structural_occurrence_projection"]["no_synthetic_observation_conversion"] is True
    assert entries["ORGANISATION_ENRICHED"]["execution_status"] == "NOT_EXECUTABLE_UNDER_CURRENT_PACK"
    assert entries["CONSTRAINT_ENRICHED"]["reason_code"] == "CONSTRAINT_COMPARATOR_NOT_MATERIALIZED"
    assert entries["FULL_RESEARCH"]["execution_status"] == "FULL_RESEARCH_HANDOFF"
    handoff = entries["FULL_RESEARCH"]["information_vector"]["handoff"]
    assert handoff["structural_term_admission"] == "NONE"
    assert handoff["mechanism_claim"] == "NONE"
    assert handoff["downstream_runtime"] == "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED"


def test_wp13_common_population_and_cutoff_are_identical_across_profiles():
    ledger = load("ProfileInformationLedger_v1.json")
    populations = {json.dumps(row["common_population"], sort_keys=True) for row in ledger["entries"]}
    assert len(populations) == 1
    only = json.loads(next(iter(populations)))
    assert only["eligible_ids_sha256"] == "2fd3464787dfa0fe24bc9540743c8483be3fc2bf239f050633a006ecb3eb1eb5"
    assert only["cutoff_schedule_sha256"] == "2b170144bc4e7c4df48bbf3a486543eed77b30d197b1f6df28e671096cfa1ea3"


def test_wp13_absence_and_marginal_ledgers_do_not_rank_profiles():
    absence = load("ProfileAbsenceDisagreementLedger_v1.json")
    marginal = load("MarginalProfileDeltaLedger_v1.json")
    assert absence["winner_synthesis"] == "FORBIDDEN"
    assert marginal["winner_synthesis"] == "FORBIDDEN"
    text = json.dumps([absence, marginal], sort_keys=True).lower()
    for forbidden in ("best_profile", "winner_profile", "recommended_profile", "promoted_profile"):
        assert forbidden not in text
    assert marginal["entries"][0]["information_delta"] == "TYPED_ABSENCE_NOT_ZERO"


def test_wp13_authority_receipt_preserves_all_reserved_denials():
    receipt = load("ESLI_WP13_REPRODUCIBILITY_AUTHORITY_RECEIPT.json")
    assert receipt["source"]["sha256"] == "63a1d24836d3cd0aaad9e5a11e9b9ec51724bfd335fab47f538ed23f36e8c58b"
    assert receipt["source"]["row_count"] == 2231
    assert receipt["source"]["eligible_record_count"] == 2036
    authority = receipt["authority"]
    assert authority["validation"] == "LOCKED_UNCONSUMED"
    assert authority["provider_fetch"] == "DENIED"
    assert authority["selector_change"] == "NONE"
    assert authority["scientific_promotion"] == "NONE"
    assert authority["semantic_admission"] == "NONE"
    assert authority["c3_activation"] == "NONE"
    assert authority["publication"] == "NONE"
    assert authority["probability_risk_exposure_execution"] == "NONE"
    assert authority["winner_synthesis"] == "FORBIDDEN"
