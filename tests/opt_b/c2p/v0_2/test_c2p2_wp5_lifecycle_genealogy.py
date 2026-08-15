from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.events import EventBuildError, build_assertion_genesis_event, build_event, event_record_hash
from ovc.opt_b.c2p_v0_2.genealogy import GenealogyError, merge, nested_in, recurrence, split
from ovc.opt_b.c2p_v0_2.lifecycle import LifecycleError, enter_dormant, reappear, retire
from ovc.opt_b.c2p_v0_2.projection import project_assertion_stream


ROOT = Path(__file__).resolve().parents[4]
PACK = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/golden/C2P2_WP5_LIFECYCLE_GENEALOGY_FIXTURES_v1.json").read_text(encoding="utf-8"))


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def assertion(seed: str, *, scale: str = "STEP") -> dict:
    members = [digest(f"{seed}-candidate-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": PACK["object_pack_id"],
        "state": "CONFIRMED",
        "member_candidate_ids": members,
        "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
        "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": scale, "partition": seed},
    }
    decision = {
        "object_pack_id": PACK["object_pack_id"],
        "terminal_decision": "NEW",
        "candidate_id": members[-1],
        "decision_id": digest(f"{seed}-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    return create_object_assertion(tracklet, decision, PACK)


def genesis(seed: str, *, scale: str = "STEP", key: str | None = None):
    obj = assertion(seed, scale=scale)
    event = build_assertion_genesis_event(
        obj,
        PACK,
        market_effective_start="2026-01-01T00:00:00Z",
        market_effective_end=None,
        evaluation_cutoff="2026-01-01T00:05:00Z",
        geometry={"coordinate": "101.000"},
        state_payload={"fixture_structure_key": key or seed},
        source_hashes=[digest(f"{seed}-source")],
    )
    return obj, event


class C2P2WP5LifecycleGenealogyTests(unittest.TestCase):
    def test_fixture_catalogue_exact_core_slice_and_synthetic_firewall(self):
        self.assertEqual([item["id"] for item in FIXTURES["fixtures"]], [f"F{number}" for number in range(17, 24)])
        self.assertEqual(PACK["status"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertFalse(PACK["activation_eligible"])
        self.assertTrue(PACK["real_source_forbidden"])

    def test_f17_dormant_reappearance_reuses_only_dormant_same_assertion(self):
        obj, first = genesis("F17", key="stable-key")
        dormant = enter_dormant(
            [first], PACK,
            market_effective_start="2026-01-01T00:06:00Z",
            first_valid_time="2026-01-01T00:07:00Z",
            evaluation_cutoff="2026-01-01T00:08:00Z",
            decision_id=digest("F17-dormant"), source_hashes=[digest("F17-dormant-source")], reason="TEMPORARY_NOT_OBSERVED",
        )
        reappeared = reappear(
            [first, dormant], PACK, fixture_structure_key="stable-key",
            market_effective_start="2026-01-01T00:09:00Z",
            first_valid_time="2026-01-01T00:10:00Z",
            evaluation_cutoff="2026-01-01T00:10:00Z",
            decision_id=digest("F17-reappear"), source_hashes=[digest("F17-reappear-source")],
        )
        snapshot = project_assertion_stream([first, dormant, reappeared])
        self.assertEqual(snapshot["object_assertion_id"], obj["object_assertion_id"])
        self.assertEqual(snapshot["lifecycle_state"], "ACTIVE")
        with self.assertRaisesRegex(LifecycleError, "CONTINUITY_KEY_MISMATCH"):
            reappear([first, dormant], PACK, fixture_structure_key="wrong", market_effective_start="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z", decision_id=digest("bad-key"), source_hashes=[digest("bad-key-source")])
        with self.assertRaisesRegex(LifecycleError, "REQUIRES_DORMANT"):
            reappear([first], PACK, fixture_structure_key="stable-key", market_effective_start="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z", decision_id=digest("active-reappear"), source_hashes=[digest("active-reappear-source")])

    def test_f18_retirement_terminal_and_recurrence_never_reuses_id(self):
        predecessor, first = genesis("F18-old", key="same-geometry")
        retired = retire(
            [first], PACK,
            market_effective_start="2026-01-01T00:06:00Z", market_effective_end="2026-01-01T00:06:00Z",
            first_valid_time="2026-01-01T00:07:00Z", evaluation_cutoff="2026-01-01T00:08:00Z",
            decision_id=digest("F18-retire"), source_hashes=[digest("F18-retire-source")], reason="EXPLICIT_SYNTHETIC_RETIREMENT",
        )
        self.assertEqual(project_assertion_stream([first, retired])["lifecycle_state"], "RETIRED")
        with self.assertRaisesRegex(LifecycleError, "REQUIRES_DORMANT"):
            reappear([first, retired], PACK, fixture_structure_key="same-geometry", market_effective_start="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z", decision_id=digest("illegal-reappear"), source_hashes=[digest("illegal-reappear-source")])

        successor, successor_genesis = genesis("F18-new", key="same-geometry")
        recurrence_event, edge = recurrence(
            [first, retired], [successor_genesis], PACK,
            market_effective_time="2026-01-01T00:11:00Z", first_valid_time="2026-01-01T00:12:00Z", evaluation_cutoff="2026-01-01T00:12:00Z",
            decision_id=digest("F18-recurrence"), source_hashes=[digest("F18-recurrence-source")],
        )
        self.assertNotEqual(predecessor["object_assertion_id"], successor["object_assertion_id"])
        self.assertEqual(edge["edge_type"], "RECURRENCE_OF")
        self.assertEqual(edge["parent_assertion_ids"], [predecessor["object_assertion_id"]])
        self.assertEqual(edge["child_assertion_ids"], [successor["object_assertion_id"]])
        self.assertFalse(recurrence_event["payload"]["continuity_claim"])

    def test_f19_split_conserves_parent_and_all_new_children(self):
        parent, parent_genesis = genesis("F19-parent")
        child_a, _ = genesis("F19-child-a")
        child_b, _ = genesis("F19-child-b")
        event, edge = split(
            [parent_genesis], [child_b, child_a], PACK, parent_disposition="RETIRED",
            market_effective_time="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z",
            decision_id=digest("F19-split"), source_hashes=[digest("F19-split-source")],
        )
        self.assertEqual(event["payload"]["parent_assertion_id"], parent["object_assertion_id"])
        self.assertEqual(set(event["payload"]["child_assertion_ids"]), {child_a["object_assertion_id"], child_b["object_assertion_id"]})
        self.assertEqual(edge["edge_type"], "SPLIT_FROM")
        self.assertEqual(set(edge["child_assertion_ids"]), {child_a["object_assertion_id"], child_b["object_assertion_id"]})
        with self.assertRaisesRegex(GenealogyError, "REQUIRES_DISTINCT_CHILDREN"):
            split([parent_genesis], [child_a, child_a], PACK, parent_disposition="ACTIVE", market_effective_time="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z", decision_id=digest("bad-split"), source_hashes=[digest("bad-split-source")])

    def test_f20_merge_preserves_all_parents_and_new_merged_identity(self):
        parent_a, _ = genesis("F20-parent-a")
        parent_b, _ = genesis("F20-parent-b")
        merged, merged_genesis = genesis("F20-merged")
        dispositions = {parent_a["object_assertion_id"]: "RETIRED", parent_b["object_assertion_id"]: "RETIRED"}
        event, edge = merge(
            [merged_genesis], [parent_b, parent_a], PACK, parent_dispositions=dispositions,
            market_effective_time="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z",
            decision_id=digest("F20-merge"), source_hashes=[digest("F20-merge-source")],
        )
        self.assertNotIn(merged["object_assertion_id"], dispositions)
        self.assertEqual(set(event["payload"]["parent_assertion_ids"]), set(dispositions))
        self.assertEqual(edge["edge_type"], "MERGED_FROM")
        self.assertEqual(set(edge["parent_assertion_ids"]), set(dispositions))
        self.assertEqual(edge["child_assertion_ids"], [merged["object_assertion_id"]])
        with self.assertRaisesRegex(GenealogyError, "DISPOSITIONS_INCOMPLETE"):
            merge([merged_genesis], [parent_a, parent_b], PACK, parent_dispositions={parent_a["object_assertion_id"]: "RETIRED"}, market_effective_time="2026-01-01T00:09:00Z", first_valid_time="2026-01-01T00:10:00Z", evaluation_cutoff="2026-01-01T00:10:00Z", decision_id=digest("bad-merge"), source_hashes=[digest("bad-merge-source")])

    def test_f21_merge_then_split_keeps_both_events_in_nonflattened_frontier(self):
        pa, _ = genesis("F21-pa")
        pb, _ = genesis("F21-pb")
        merged, mg = genesis("F21-merged")
        merge_event, _ = merge([mg], [pa, pb], PACK, parent_dispositions={pa["object_assertion_id"]: "RETIRED", pb["object_assertion_id"]: "RETIRED"}, market_effective_time="2026-01-01T00:06:00Z", first_valid_time="2026-01-01T00:07:00Z", evaluation_cutoff="2026-01-01T00:07:00Z", decision_id=digest("F21-merge"), source_hashes=[digest("F21-merge-source")])
        ca, _ = genesis("F21-ca")
        cb, _ = genesis("F21-cb")
        split_event, _ = split([mg, merge_event], [ca, cb], PACK, parent_disposition="RETIRED", market_effective_time="2026-01-01T00:08:00Z", first_valid_time="2026-01-01T00:09:00Z", evaluation_cutoff="2026-01-01T00:09:00Z", decision_id=digest("F21-split"), source_hashes=[digest("F21-split-source")])
        snapshot = project_assertion_stream([split_event, mg, merge_event])
        self.assertEqual(snapshot["state_payload"]["genealogy_event_ids"], sorted([merge_event["event_id"], split_event["event_id"]]))

    def test_f22_nested_objects_remain_separate_and_relation_is_nonidentity(self):
        parent, pg = genesis("F22-parent")
        child, cg = genesis("F22-child")
        edge = nested_in([pg], [cg], market_effective_time="2026-01-01T00:06:00Z", first_valid_time="2026-01-01T00:07:00Z", evaluation_cutoff="2026-01-01T00:07:00Z")
        self.assertNotEqual(parent["object_assertion_id"], child["object_assertion_id"])
        self.assertEqual(edge["edge_type"], "NESTED_IN")
        self.assertEqual(edge["parent_assertion_ids"], [parent["object_assertion_id"]])
        self.assertEqual(edge["child_assertion_ids"], [child["object_assertion_id"]])

    def test_f23_same_structure_across_scales_never_reuses_assertion_id(self):
        a15, _ = genesis("F23-same", scale="15M", key="shared-key")
        a2h, _ = genesis("F23-same", scale="2H", key="shared-key")
        self.assertNotEqual(a15["object_assertion_id"], a2h["object_assertion_id"])

    def test_unresolved_match_decision_cannot_emit_lifecycle_mutation(self):
        _, first = genesis("F47")
        with self.assertRaisesRegex(EventBuildError, "UNRESOLVED_DECISION_CANNOT_MUTATE"):
            build_event(stream_id=first["stream_id"], sequence_no=1, event_type="ENTER_DORMANT", object_pack=PACK, market_effective_start="2026-01-01T00:06:00Z", market_effective_end=None, first_valid_time="2026-01-01T00:07:00Z", evaluation_cutoff="2026-01-01T00:07:00Z", decision_id=digest("F47-ambiguous"), parent_event_ids=[first["event_id"]], source_hashes=[digest("F47-source")], payload={"match_decision_terminal": "AMBIGUOUS"}, prior_event_hash=event_record_hash(first))


if __name__ == "__main__":
    unittest.main()
