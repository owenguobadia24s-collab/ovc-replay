import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.boundary_pack import boundary_pack_id, compatibility_disposition, freeze_pack
from ovc.opt_b.c2e_v2.models import C2EModelError, RECORD_SPECS, build_record, identity_fields, validate_record
from ovc.opt_b.c2e_v2.serialization import C2ESerializationError, canonical_decimal

ROOT = Path(__file__).resolve().parents[4]
FIX = ROOT / "fixtures/opt_b/c2e/v0_2/wp2"
SCHEMAS = ROOT / "schemas/opt_b/c2e/v0_2"


class C2E2WP2ObjectModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((FIX / "object_cases.json").read_text())
        cls.pack = json.loads((FIX / "boundary_pack.json").read_text())

    def test_every_semantic_object_builds_and_round_trips(self):
        for kind in RECORD_SPECS:
            record = build_record(kind, self.cases[kind])
            self.assertEqual(validate_record(kind, record), record, kind)
            self.assertIn("logical_hash", record)

    def test_all_wp2_schema_files_exist_and_parse(self):
        required = {
            "c2e_episode_genesis_v0_2.schema.json", "c2e_episode_snapshot_v0_2.schema.json",
            "c2e_phase_segment_v0_2.schema.json", "c2e_boundary_event_v0_2.schema.json",
            "c2e_lineage_edge_v0_2.schema.json", "c2e_membership_delta_v0_2.schema.json",
            "c2e_remap_record_v0_2.schema.json", "c2e_stream_manifest_v0_2.schema.json",
            "c2e_boundary_pack_v0_2.schema.json", "c2e_boundary_rule_v0_2.schema.json",
            "c2e_compatibility_matrix_v0_2.schema.json", "c2e_checkpoint_v0_2.schema.json",
            "c2e_sri_handoff_v0_1.schema.json",
        }
        self.assertTrue(required.issubset({path.name for path in SCHEMAS.iterdir()}))
        for name in required:
            self.assertIsInstance(json.loads((SCHEMAS / name).read_text()), dict)

    def test_genesis_identity_excludes_future_membership_and_status(self):
        fields = set(identity_fields("episode_genesis"))
        for forbidden in ("member_ids", "end_time", "status", "terminal_boundary_id", "snapshot_ids", "family_id", "semantic_label", "outcome"):
            self.assertNotIn(forbidden, fields)
        invalid = copy.deepcopy(self.cases["episode_genesis"])
        invalid["member_ids"] = ["FUTURE.MEMBER"]
        with self.assertRaisesRegex(C2EModelError, "GENESIS_FUTURE_FIELD_DENIED"):
            build_record("episode_genesis", invalid)

    def test_remap_is_comparison_only_and_not_sri_identity(self):
        record = build_record("remap_record", self.cases["remap_record"])
        self.assertTrue(record["comparison_only"])
        self.assertEqual(record["authority"], "COMPARISON_ONLY")
        invalid = copy.deepcopy(self.cases["remap_record"])
        invalid["comparison_only"] = False
        with self.assertRaisesRegex(C2EModelError, "REMAP_COMPARISON_ONLY_REQUIRED"):
            build_record("remap_record", invalid)
        self.assertNotIn("remap_record_id", identity_fields("sri_handoff"))

    def test_sri_producer_contract_cannot_own_representation_or_family_semantics(self):
        record = build_record("sri_handoff", self.cases["sri_handoff"])
        self.assertEqual(record["authority"], "READ_ONLY_PRODUCER_HANDOFF")
        invalid = copy.deepcopy(self.cases["sri_handoff"])
        invalid["family"] = "FAMILY.001"
        with self.assertRaisesRegex(C2EModelError, "SRI_PRODUCER_OWNERSHIP_BREACH"):
            build_record("sri_handoff", invalid)

    def test_numeric_canonicalization_edge_cases(self):
        self.assertEqual(canonical_decimal("1.25", 4), "1.2500")
        self.assertEqual(canonical_decimal("1.2500", 4), "1.2500")
        self.assertEqual(canonical_decimal("-0.0000", 4), "0.0000")
        self.assertEqual(canonical_decimal(0, 0), "0")
        for value, marker in ((float("nan"), "RUNTIME_FLOAT_IDENTITY_DENIED"), ("NaN", "DECIMAL_NONFINITE_DENIED"), ("Infinity", "DECIMAL_NONFINITE_DENIED"), ("1e-3", "DECIMAL_EXPONENT_FORM_DENIED"), ("1.23456", "DECIMAL_PRECISION_MISMATCH")):
            with self.assertRaisesRegex(C2ESerializationError, marker):
                canonical_decimal(value, 4)

    def test_boundary_pack_identity_is_order_and_metadata_invariant(self):
        original = freeze_pack(self.pack)
        reordered = copy.deepcopy(self.pack)
        reordered["rules"] = list(reversed(reordered["rules"]))
        reordered["metadata"] = {"description":"changed diagnostic metadata", "unrelated":42}
        reordered["rules"][0]["parameters"] = dict(reversed(list(reordered["rules"][0]["parameters"].items())))
        self.assertEqual(boundary_pack_id(self.pack), boundary_pack_id(reordered))
        self.assertEqual(original["boundary_pack_id"], freeze_pack(reordered)["boundary_pack_id"])

    def test_identity_parameter_and_precision_changes_create_new_pack(self):
        base = boundary_pack_id(self.pack)
        changed = copy.deepcopy(self.pack)
        changed["rules"][0]["parameters"]["threshold"] = "0.250001"
        self.assertNotEqual(base, boundary_pack_id(changed))
        precision_changed = copy.deepcopy(self.pack)
        precision_changed["rules"][0]["parameter_precisions"]["threshold"] = 7
        self.assertNotEqual(base, boundary_pack_id(precision_changed))

    def test_compatibility_is_symmetric_and_undeclared_fails_closed(self):
        self.assertEqual(compatibility_disposition(self.pack, "BIRTH_CANDIDATE", "CONTINUATION_CANDIDATE"), "ORDERED_BY_PRIORITY")
        self.assertEqual(compatibility_disposition(self.pack, "CONTINUATION_CANDIDATE", "BIRTH_CANDIDATE"), "ORDERED_BY_PRIORITY")
        self.assertEqual(compatibility_disposition(self.pack, "BIRTH_CANDIDATE", "UNKNOWN"), "UNDECLARED_FAIL_CLOSED")

    def test_pack_is_never_active_or_canonical(self):
        frozen = freeze_pack(self.pack)
        self.assertFalse(frozen["active"])
        self.assertFalse(frozen["canonical"])
        self.assertEqual(frozen["authority"], "SHADOW")


if __name__ == "__main__":
    unittest.main()
