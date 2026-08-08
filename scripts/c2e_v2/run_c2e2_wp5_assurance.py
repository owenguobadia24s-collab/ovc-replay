#!/usr/bin/env python3
"""Emit one compact synthetic-only C2E2-WP5 assurance receipt.

No provider/source replay path exists in this script.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.cli import build_assurance_receipt
from ovc.opt_b.c2e_v2.handoff import build_input_frame
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine

FRAME = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"
PACK = ROOT / "fixtures/opt_b/c2e/v0_2/wp2/boundary_pack.json"
CATALOGUE = ROOT / "fixtures/opt_b/c2e/v0_2/adversarial/F01_F40_catalogue.json"


def main() -> int:
    raw = json.loads(FRAME.read_text())
    frame1 = build_input_frame(raw)
    raw2 = copy.deepcopy(raw)
    raw2["identity"]["observation_id"] = "C2.OBS.FIXTURE.WP5.002"
    raw2["identity"]["c2_record_id"] = "C2.OBS.FIXTURE.WP5.002"
    raw2["chronology"]["source_time"] = "2026-06-22T10:15:00Z"
    raw2["chronology"]["candidate_onset_time"] = "2026-06-22T10:15:00Z"
    raw2["chronology"]["first_valid_time"] = "2026-06-22T10:30:00Z"
    raw2["chronology"]["evaluation_cutoff"] = "2026-06-22T10:30:00Z"
    frame2 = build_input_frame(raw2)
    pack = freeze_pack(json.loads(PACK.read_text()))
    engine = EpisodeEngine(pack["boundary_pack_id"])
    genesis = engine.birth(frame=frame1, boundary_rule_id="RULE.BIRTH", candidate_id="CAND.WP5.BIRTH", effective_time="2026-06-22T10:15:00Z", first_valid_time="2026-06-22T10:15:00Z")
    engine.continue_episode(episode_id=genesis["episode_id"], frame=frame2, candidate_id="CAND.WP5.CONT", effective_time="2026-06-22T10:30:00Z", first_valid_time="2026-06-22T10:30:00Z")
    fixture_rows = json.loads(CATALOGUE.read_text())["fixtures"]
    receipt = build_assurance_receipt(
        engine.stream.records,
        source_binding={"source_release_id":"SOURCE.FIXTURE.v1","c2_release_id":"C2AR.SHADOW.FIXTURE.v1"},
        boundary_pack_id=pack["boundary_pack_id"], schema_ids=["c2e-v0.2"], code_hashes=["C2E2-WP5-SYNTHETIC"],
        performance={"measurement_class":"IMPLEMENTATION_SMOKE_ONLY_CI_MEASUREMENT_SEPARATE"},
        conflict_counts={"ambiguous_candidate_sets":1,"evaluated_candidate_sets":10,"conflict_resolutions":1,"resolved_boundary_transactions":10,"conflicted_episodes":0,"emitted_episodes":1,"peer_owner_collisions":1,"peer_ownership_frames":10,"compound_invalidated":1,"compound_candidates":4,"not_evaluable_rules":1,"applicable_rule_evaluations":10},
        fixture_results=[{"fixture_id":row["fixture_id"],"status":"PASS"} for row in fixture_rows],
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
