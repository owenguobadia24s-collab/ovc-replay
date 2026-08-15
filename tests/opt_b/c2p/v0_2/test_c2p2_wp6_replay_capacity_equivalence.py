from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.capacity import CapacityPolicyError, evaluate_capacity
from ovc.opt_b.c2p_v0_2.checkpoint import CheckpointIntegrityError, build_checkpoint, restore_checkpoint
from ovc.opt_b.c2p_v0_2.events import build_assertion_genesis_event
from ovc.opt_b.c2p_v0_2.ledger import CanonicalEventLedger
from ovc.opt_b.c2p_v0_2.replay import prove_replay_equivalence, replay_events
from ovc.opt_b.c2p_v0_2.retrieval import ExactHardScopeIndex, prove_dynamic_retrieval_equivalence, static_retrieval_equivalence_contract


ROOT = Path(__file__).resolve().parents[4]
PACK = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/golden/C2P2_WP6_REPLAY_CAPACITY_FIXTURES_v1.json").read_text(encoding="utf-8"))


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def assertion(seed: str, *, partition: str = "P") -> dict:
    members = [digest(f"{seed}-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": PACK["object_pack_id"], "state": "CONFIRMED",
        "member_candidate_ids": members, "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z", "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": partition},
    }
    decision = {
        "object_pack_id": PACK["object_pack_id"], "terminal_decision": "NEW",
        "candidate_id": members[-1], "decision_id": digest(f"{seed}-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z", "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    return create_object_assertion(tracklet, decision, PACK)


def genesis(seed: str, *, partition: str = "P"):
    obj = assertion(seed, partition=partition)
    event = build_assertion_genesis_event(
        obj, PACK, market_effective_start="2026-01-01T00:00:00Z", market_effective_end=None,
        evaluation_cutoff="2026-01-01T00:05:00Z", geometry={"coordinate": "101.000"},
        state_payload={"fixture_structure_key": seed}, source_hashes=[digest(f"{seed}-source")],
    )
    return obj, event


class C2P2WP6ReplayCapacityEquivalenceTests(unittest.TestCase):
    def test_fixture_catalogue_and_synthetic_firewall(self):
        self.assertEqual(PACK["status"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertFalse(PACK["activation_eligible"])
        ids = {item["id"] for item in FIXTURES["fixtures"]}
        self.assertTrue({"F10", "F37", "F39", "F40", "F45", "CAP-T0", "CAP-T1", "CAP-T2", "CAP-T3"}.issubset(ids))

    def test_replay_is_order_chunk_and_worker_layout_invariant(self):
        _, a = genesis("A", partition="A")
        _, b = genesis("B", partition="B")
        reference = replay_events([a, b])
        reversed_layout = replay_events([b, a], chunk_size=1, worker_partitions=4)
        self.assertEqual(reference.ledger_digest, reversed_layout.ledger_digest)
        self.assertEqual(reference.projection_digest, reversed_layout.projection_digest)
        self.assertTrue(prove_replay_equivalence([a, b], [b, a]))

    def test_checkpoint_restart_is_byte_equivalent_and_corruption_fails_closed(self):
        obj, event = genesis("F37")
        ledger = CanonicalEventLedger.from_events([event])
        checkpoint = build_checkpoint(ledger, assertion_ids=[obj["object_assertion_id"]], index_digest=digest("index"))
        restored = restore_checkpoint(checkpoint)
        self.assertEqual(ledger.canonical_export_bytes(), restored.canonical_export_bytes())
        self.assertEqual(ledger.seal(), restored.seal())
        corrupt = deepcopy(checkpoint)
        corrupt["ledger_digest"] = digest("corrupt")
        with self.assertRaisesRegex(CheckpointIntegrityError, "HASH_MISMATCH"):
            restore_checkpoint(corrupt)

    def test_exact_hard_scope_index_proves_static_and_dynamic_equivalence(self):
        assertions = [assertion(f"F45-{index}", partition="P") for index in range(128)]
        off_scope = assertion("off-scope", partition="Q")
        all_assertions = assertions + [off_scope]
        candidate = {
            "candidate_id": digest("candidate"), "object_pack_id": PACK["object_pack_id"],
            "structural_role_id": "LEVEL", "geometry_kind_id": "POINT_REFERENCE",
            "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": "P"},
        }
        index = ExactHardScopeIndex.build(list(reversed(all_assertions)))
        proof = prove_dynamic_retrieval_equivalence(candidate, all_assertions, PACK, index)
        self.assertEqual(proof["result"], "PASS_EXACT_EQUIVALENCE")
        self.assertEqual(len(proof["reference_assertion_ids"]), 128)
        static = static_retrieval_equivalence_contract()
        self.assertEqual(static["reference_scope_fields"], static["optimized_key_fields"])
        self.assertEqual(static["authority"], "NON_AUTHORITATIVE_RETRIEVAL_ONLY")

    def test_capacity_tiers_fail_or_defer_without_semantic_weakening(self):
        envelope = {"memory_bytes": 100, "wall_clock_ms": 100}
        observed = {"memory_bytes": 101, "wall_clock_ms": 90}
        expected = {
            "T0_IDENTITY_BEARING": "CAPACITY_EXCEEDED",
            "T1_OPTIONAL_ENRICHMENT": "DEFER_OPTIONAL_ENRICHMENT",
            "T2_REBUILDABLE_PROJECTION": "DEFER_REBUILDABLE_PROJECTION",
            "T3_OPTIMIZED_INDEX": "FALLBACK_TO_EXACT_REFERENCE",
        }
        for tier, disposition in expected.items():
            receipt = evaluate_capacity(tier=tier, authorized_envelope=envelope, observed_consumption=observed, last_completed_checkpoint="cp-1")
            self.assertEqual(receipt["disposition"], disposition)
            self.assertEqual(receipt["semantic_contract"]["sampling"], "FORBIDDEN")
            self.assertEqual(receipt["semantic_contract"]["reduced_precision"], "FORBIDDEN")
        with self.assertRaisesRegex(CapacityPolicyError, "SEMANTIC_CHANGE_FORBIDDEN"):
            evaluate_capacity(tier="T0_IDENTITY_BEARING", authorized_envelope=envelope, observed_consumption=observed, semantic_change={"sampling": True})

    def test_capacity_pass_is_deterministic(self):
        kwargs = dict(tier="T0_IDENTITY_BEARING", authorized_envelope={"memory_bytes": 100}, observed_consumption={"memory_bytes": 99})
        first = evaluate_capacity(**kwargs)
        second = evaluate_capacity(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["disposition"], "PASS")


if __name__ == "__main__":
    unittest.main()
