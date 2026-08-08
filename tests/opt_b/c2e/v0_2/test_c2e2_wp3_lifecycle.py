import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.candidate import build_candidate
from ovc.opt_b.c2e_v2.handoff import build_input_frame
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine, LifecycleError
from ovc.opt_b.c2e_v2.resolver import resolve_candidates
from ovc.opt_b.c2e_v2.stream import AppendOnlyStream, StreamError
from ovc.opt_b.c2e_v2.topology import TopologyError

ROOT = Path(__file__).resolve().parents[4]
WP1 = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"
WP2 = ROOT / "fixtures/opt_b/c2e/v0_2/wp2/boundary_pack.json"
WP3 = ROOT / "fixtures/opt_b/c2e/v0_2/wp3/resolver_pack.json"


def frame_at(observation_suffix: str, source_time: str, first_valid: str):
    payload = json.loads(WP1.read_text())
    payload["identity"]["observation_id"] = f"C2.OBS.FIXTURE.{observation_suffix}"
    payload["identity"]["c2_record_id"] = f"C2.OBS.FIXTURE.{observation_suffix}"
    payload["chronology"]["source_time"] = source_time
    payload["chronology"]["candidate_onset_time"] = source_time
    payload["chronology"]["first_valid_time"] = first_valid
    payload["chronology"]["evaluation_cutoff"] = first_valid
    return build_input_frame(payload)


def rule(pack, rule_id):
    return next(item for item in pack["rules"] if item["boundary_rule_id"] == rule_id)


class C2E2WP3LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(WP3.read_text())
        cls.pack_id = freeze_pack(json.loads(WP2.read_text()))["boundary_pack_id"]
        cls.frame1 = frame_at("101", "2026-06-22T10:00:00Z", "2026-06-22T10:15:00Z")
        cls.frame2 = frame_at("102", "2026-06-22T10:15:00Z", "2026-06-22T10:30:00Z")
        cls.frame3 = frame_at("103", "2026-06-22T10:30:00Z", "2026-06-22T10:45:00Z")

    def test_candidate_dependency_missingness_is_selective(self):
        candidate = build_candidate(rule(self.pack, "R.CONT"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        self.assertIsNotNone(candidate)
        self.assertTrue(candidate["evaluable"])
        blocked_rule = copy.deepcopy(rule(self.pack, "R.CONT"))
        blocked_rule["dependencies"]["REQUIRED"] = ["DEP.DOES.NOT.EXIST"]
        with self.assertRaisesRegex(Exception, "DEP_UNDECLARED_RESULT_MISSING"):
            build_candidate(blocked_rule, self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")

    def test_equal_priority_incompatibility_never_gets_lexical_winner(self):
        a = build_candidate(rule(self.pack, "R.A"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        c = build_candidate(rule(self.pack, "R.C"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        result = resolve_candidates(self.pack, [c, a])
        self.assertEqual(result["status"], "CONFLICT")
        self.assertEqual(result["resolved"], [])
        self.assertIn("C2E_EQUAL_PRIORITY_INCOMPATIBLE", result["reason_codes"])

    def test_non_transitive_compatibility_fails_compound_closure(self):
        candidates = [build_candidate(rule(self.pack, rid), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z") for rid in ("R.A","R.B","R.C")]
        result = resolve_candidates(self.pack, candidates)
        self.assertEqual(result["status"], "CONFLICT")

    def test_higher_priority_effect_invalidates_lower_candidate(self):
        gap = build_candidate(rule(self.pack, "R.GAP"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        cont = build_candidate(rule(self.pack, "R.CONT"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z", invalidated_by_actions=["CENSOR_GAP"])
        result = resolve_candidates(self.pack, [cont, gap])
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual([item["lifecycle_action"] for item in result["resolved"]], ["CENSOR_GAP"])
        self.assertEqual(result["suppressed"][0]["suppression_reason"], "HIGHER_PRIORITY_EFFECT_INVALIDATED")

    def test_resolver_is_candidate_permutation_invariant(self):
        a = build_candidate(rule(self.pack, "R.A"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        b = build_candidate(rule(self.pack, "R.B"), self.frame1, matched=True, effective_time="2026-06-22T10:15:00Z")
        left = resolve_candidates(self.pack, [a,b])
        right = resolve_candidates(self.pack, [b,a])
        self.assertEqual(left, right)
        self.assertEqual(left["status"], "RESOLVED")

    def test_birth_continuation_phase_and_release_end_are_append_only(self):
        engine = EpisodeEngine(self.pack_id)
        genesis = engine.birth(frame=self.frame1,boundary_rule_id="R.BIRTH",candidate_id="CAND.BIRTH",effective_time="2026-06-22T10:15:00Z",first_valid_time="2026-06-22T10:15:00Z")
        original = copy.deepcopy(genesis)
        engine.continue_episode(episode_id=genesis["episode_id"],frame=self.frame2,candidate_id="CAND.CONT",effective_time="2026-06-22T10:30:00Z",first_valid_time="2026-06-22T10:30:00Z")
        engine.phase_mutation(episode_id=genesis["episode_id"],candidate_id="CAND.PHASE",phase_type="SYNTHETIC_PHASE",start_time="2026-06-22T10:15:00Z",end_time="2026-06-22T10:30:00Z",source_record_ids=[self.frame1["frame_id"],self.frame2["frame_id"]],effective_time="2026-06-22T10:30:00Z",first_valid_time="2026-06-22T10:30:00Z")
        engine.censor(episode_id=genesis["episode_id"],candidate_id="CAND.RELEASE",reason="CENSOR_RELEASE_END",effective_time="2026-06-22T10:45:00Z",first_valid_time="2026-06-22T10:45:00Z")
        self.assertEqual(engine.genesis[genesis["episode_id"]], original)
        snapshot = engine.snapshot(genesis["episode_id"],as_of_time="2026-06-22T10:45:00Z",first_valid_time="2026-06-22T10:45:00Z")
        self.assertEqual(snapshot["status"], "CENSORED")
        self.assertEqual(len(snapshot["member_ids"]), 2)
        with self.assertRaisesRegex(LifecycleError, "EPISODE_NOT_OPEN"):
            engine.continue_episode(episode_id=genesis["episode_id"],frame=self.frame3,candidate_id="CAND.REOPEN",effective_time="2026-06-22T10:45:00Z",first_valid_time="2026-06-22T10:45:00Z")

    def test_single_owner_collision_fails_closed(self):
        engine = EpisodeEngine(self.pack_id)
        first = engine.birth(frame=self.frame1,boundary_rule_id="R.BIRTH",candidate_id="CAND.1",effective_time="2026-06-22T10:15:00Z",first_valid_time="2026-06-22T10:15:00Z")
        with self.assertRaisesRegex(LifecycleError, "C2E_OWNER_MULTIPLE_PEER_OWNERS"):
            engine.birth(frame=self.frame1,boundary_rule_id="R.BIRTH",candidate_id="CAND.2",effective_time="2026-06-22T10:15:00Z",first_valid_time="2026-06-22T10:15:00Z")

    def test_topology_cycle_is_denied_without_appending_failed_event(self):
        engine = EpisodeEngine(self.pack_id)
        a = engine.birth(frame=self.frame1,boundary_rule_id="R.BIRTH",candidate_id="CAND.A",effective_time="2026-06-22T10:15:00Z",first_valid_time="2026-06-22T10:15:00Z")
        b = engine.birth(frame=self.frame2,boundary_rule_id="R.BIRTH",candidate_id="CAND.B",effective_time="2026-06-22T10:30:00Z",first_valid_time="2026-06-22T10:30:00Z")
        engine.link(edge_type="NEST",parent_episode_id=a["episode_id"],child_episode_id=b["episode_id"],candidate_id="CAND.NEST",effective_time="2026-06-22T10:30:00Z",first_valid_time="2026-06-22T10:30:00Z")
        before = len(engine.stream.records)
        with self.assertRaisesRegex(TopologyError, "C2E_TOPOLOGY_CYCLE"):
            engine.link(edge_type="NEST",parent_episode_id=b["episode_id"],child_episode_id=a["episode_id"],candidate_id="CAND.CYCLE",effective_time="2026-06-22T10:45:00Z",first_valid_time="2026-06-22T10:45:00Z")
        self.assertEqual(len(engine.stream.records), before)

    def test_stream_has_no_update_or_delete_path(self):
        engine = EpisodeEngine(self.pack_id)
        genesis = engine.birth(frame=self.frame1,boundary_rule_id="R.BIRTH",candidate_id="CAND.BIRTH",effective_time="2026-06-22T10:15:00Z",first_valid_time="2026-06-22T10:15:00Z")
        stream = engine.stream
        with self.assertRaisesRegex(StreamError, "APPEND_ONLY_UPDATE_DENIED"):
            stream.update(genesis)
        with self.assertRaisesRegex(StreamError, "APPEND_ONLY_DELETE_DENIED"):
            stream.delete(genesis["episode_id"])
        with self.assertRaisesRegex(StreamError, "APPEND_ONLY_DUPLICATE_OR_UPDATE_DENIED"):
            stream.append(genesis)


if __name__ == "__main__":
    unittest.main()
