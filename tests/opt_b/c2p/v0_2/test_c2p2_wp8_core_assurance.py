from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.capacity import evaluate_capacity
from ovc.opt_b.c2p_v0_2.checkpoint import build_checkpoint, restore_checkpoint
from ovc.opt_b.c2p_v0_2.events import build_assertion_genesis_event
from ovc.opt_b.c2p_v0_2.genealogy import recurrence
from ovc.opt_b.c2p_v0_2.integrations import build_c3_entity_temporal_reference, build_console_read_model
from ovc.opt_b.c2p_v0_2.ledger import CanonicalEventLedger
from ovc.opt_b.c2p_v0_2.lifecycle import enter_dormant, reappear, retire
from ovc.opt_b.c2p_v0_2.projection import project_assertion_stream
from ovc.opt_b.c2p_v0_2.replay import prove_replay_equivalence


ROOT = Path(__file__).resolve().parents[4]
MATRIX = json.loads((ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-wp8/C2P2_WP8_CORE_ASSURANCE_MATRIX_v1.json").read_text(encoding="utf-8"))
PACK = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json").read_text(encoding="utf-8"))


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def make_assertion(seed: str) -> tuple[dict, dict]:
    members = [digest(f"{seed}-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": PACK["object_pack_id"],
        "state": "CONFIRMED",
        "member_candidate_ids": members,
        "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
        "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": seed},
    }
    decision = {
        "object_pack_id": PACK["object_pack_id"],
        "terminal_decision": "NEW",
        "candidate_id": members[-1],
        "decision_id": digest(f"{seed}-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    obj = create_object_assertion(tracklet, decision, PACK)
    event = build_assertion_genesis_event(
        obj,
        PACK,
        market_effective_start="2026-01-01T00:00:00Z",
        market_effective_end=None,
        evaluation_cutoff="2026-01-01T00:05:00Z",
        geometry={"coordinate": "101.000"},
        state_payload={"fixture_structure_key": seed},
        source_hashes=[digest(f"{seed}-source")],
    )
    return obj, event


class C2P2WP8CoreAssuranceTests(unittest.TestCase):
    def test_ratified_core_and_deferred_catalogues_are_exact_and_disjoint(self):
        core = MATRIX["core_fixture_ids"]
        deferred = MATRIX["deferred_reconciliation_fixture_ids"]
        self.assertEqual(len(core), 39)
        self.assertEqual(len(deferred), 9)
        self.assertEqual(len(set(core)), 39)
        self.assertEqual(set(core) & set(deferred), set())
        self.assertEqual(len(MATRIX["core_qa_ids"]), 37)
        self.assertEqual(MATRIX["deferred_reconciliation_qa_ids"], ["QA-024", "QA-025", "QA-026", "QA-027"])
        self.assertEqual(set(MATRIX["core_qa_ids"]) & set(MATRIX["deferred_reconciliation_qa_ids"]), set())

    def test_every_core_packet_test_surface_exists(self):
        test_root = ROOT / "tests/opt_b/c2p/v0_2"
        missing = [name for name in MATRIX["packet_test_surfaces"] if not (test_root / name).exists()]
        self.assertEqual(missing, [])

    def test_terminal_authority_is_non_activation_and_followons_remain_deferred(self):
        terminal = MATRIX["terminal_authority"]
        self.assertEqual(terminal["terminal_state"], "C2P2_CORE_IMPLEMENTED_SHADOW_CONFORMANT")
        self.assertEqual(terminal["c2p_runtime"], "NONE")
        self.assertEqual(terminal["empirical_object_pack_selection"], "NONE")
        self.assertTrue(terminal["real_source_replay"].startswith("DENIED_"))
        self.assertEqual(terminal["validation"], "LOCKED_UNCONSUMED")
        self.assertEqual(MATRIX["deferred_follow_ons"], ["C2P2-PS0", "C2P2-RS0", "C2P2-RR0", "C2P2-AG0"])
        self.assertEqual(STATE["authority"]["c2p_runtime"], "NONE")
        self.assertEqual(STATE["authority"]["validation"], "LOCKED_UNCONSUMED")

    def test_integrated_synthetic_lifecycle_replay_checkpoint_and_read_model(self):
        predecessor, genesis = make_assertion("wp8-predecessor")
        dormant = enter_dormant(
            [genesis], PACK,
            market_effective_start="2026-01-01T00:06:00Z",
            first_valid_time="2026-01-01T00:07:00Z",
            evaluation_cutoff="2026-01-01T00:07:00Z",
            decision_id=digest("wp8-dormant"), source_hashes=[digest("wp8-dormant-source")], reason="SYNTHETIC_GAP",
        )
        reappeared = reappear(
            [genesis, dormant], PACK, fixture_structure_key="wp8-predecessor",
            market_effective_start="2026-01-01T00:08:00Z", first_valid_time="2026-01-01T00:09:00Z",
            evaluation_cutoff="2026-01-01T00:09:00Z", decision_id=digest("wp8-reappear"), source_hashes=[digest("wp8-reappear-source")],
        )
        retired = retire(
            [genesis, dormant, reappeared], PACK,
            market_effective_start="2026-01-01T00:10:00Z", market_effective_end="2026-01-01T00:10:00Z",
            first_valid_time="2026-01-01T00:11:00Z", evaluation_cutoff="2026-01-01T00:11:00Z",
            decision_id=digest("wp8-retire"), source_hashes=[digest("wp8-retire-source")], reason="SYNTHETIC_TERMINAL",
        )
        predecessor_stream = [genesis, dormant, reappeared, retired]
        self.assertEqual(project_assertion_stream(predecessor_stream)["lifecycle_state"], "RETIRED")

        successor, successor_genesis = make_assertion("wp8-successor")
        recurrence_event, edge = recurrence(
            predecessor_stream, [successor_genesis], PACK,
            market_effective_time="2026-01-01T00:12:00Z", first_valid_time="2026-01-01T00:13:00Z",
            evaluation_cutoff="2026-01-01T00:13:00Z", decision_id=digest("wp8-recurrence"), source_hashes=[digest("wp8-recurrence-source")],
        )
        self.assertNotEqual(predecessor["object_assertion_id"], successor["object_assertion_id"])
        self.assertEqual(edge["edge_type"], "RECURRENCE_OF")
        successor_stream = [successor_genesis, recurrence_event]

        all_events = predecessor_stream + successor_stream
        ledger = CanonicalEventLedger.from_events(all_events)
        checkpoint = build_checkpoint(ledger, assertion_ids=[predecessor["object_assertion_id"], successor["object_assertion_id"]])
        restored = restore_checkpoint(checkpoint)
        self.assertEqual(restored.canonical_export_bytes(), ledger.canonical_export_bytes())
        self.assertTrue(prove_replay_equivalence(all_events, list(reversed(all_events))))

        successor_snapshot = project_assertion_stream(successor_stream)
        c3 = build_c3_entity_temporal_reference(successor_snapshot)
        console = build_console_read_model(successor_snapshot)
        self.assertEqual(c3["entity_ref"]["logical_id"], successor["object_assertion_id"])
        self.assertFalse(c3["persistence_inference"])
        self.assertTrue(console["read_only"])
        self.assertEqual(console["write_capabilities"], [])

    def test_capacity_pressure_never_changes_identity_semantics(self):
        receipt = evaluate_capacity(
            tier="T0_IDENTITY_BEARING",
            authorized_envelope={"memory_bytes": 100, "wall_clock_ms": 100},
            observed_consumption={"memory_bytes": 101, "wall_clock_ms": 90},
            last_completed_checkpoint="wp8-cp",
        )
        self.assertEqual(receipt["disposition"], "CAPACITY_EXCEEDED")
        self.assertEqual(receipt["semantic_contract"]["sampling"], "FORBIDDEN")
        self.assertEqual(receipt["semantic_contract"]["reduced_precision"], "FORBIDDEN")
        self.assertEqual(PACK["status"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertFalse(PACK["activation_eligible"])
        self.assertTrue(PACK["real_source_forbidden"])


if __name__ == "__main__":
    unittest.main()
