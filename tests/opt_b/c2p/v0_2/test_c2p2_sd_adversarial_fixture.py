from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.c2p_v0_2.sd_discrimination import CANDIDATE_IDS, analyze_edge, make_edge

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "tests/fixtures/c2p2_sd/adversarial_scenarios_v0_1.json"


def test_adversarial_scenarios_match_frozen_failure_taxonomy() -> None:
    fixture = json.loads(FIXTURE.read_text())
    assert fixture["authority_effect"] == "NONE_SYNTHETIC_ONLY"
    assert len(fixture["scenarios"]) == 6

    for ordinal, scenario in enumerate(fixture["scenarios"]):
        dispositions = {
            candidate_id: value
            for candidate_id, value in zip(CANDIDATE_IDS, scenario["candidate_dispositions"], strict=True)
        }
        edge = make_edge(
            prior_source_record_id=f"P-{ordinal}",
            current_source_record_id=f"C-{ordinal}",
            first_valid_time=f"2021-01-01T00:{ordinal:02d}:00Z",
            evaluation_cutoff="2021-01-01T01:00:00Z",
            instrument="GBPUSD",
            side="BID",
            clock="15M",
            structural_role_id="ROLE_LEVEL",
            geometry_kind_id="LEVEL",
            candidate_dispositions=dispositions,
            confirmed_hard_breaks=scenario["confirmed_hard_breaks"],
            owner_constitution_evidence={"hard_scope_constant": True},
        )
        record = analyze_edge(edge)
        assert record["include_in_disagreement_ledger"] is scenario["expected_ledger"]
        expected = [CANDIDATE_IDS[index] for index in scenario["expected_hard_falsification_slots"]]
        assert record["hard_falsification_candidate_ids"] == expected
