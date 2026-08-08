import json
from decimal import Decimal
from pathlib import Path
import unittest

from ovc.opt_b.sfc.serialization import SFCSerializationError, canonical_json_bytes, logical_hash

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "schemas/opt_b/sfc"
REG_DIR = ROOT / "registries/opt_b/sfc"


class SFCWP1ContractTests(unittest.TestCase):
    def test_canonical_serialization_is_order_independent_and_hash_stable(self):
        left = {"b": [2, 1], "a": {"z": Decimal("1.2300"), "n": -0.0}}
        right = {"a": {"n": 0.0, "z": Decimal("1.23")}, "b": [2, 1]}
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(logical_hash(left), logical_hash(right))

    def test_nonfinite_values_fail_closed(self):
        for bad in (float("nan"), float("inf"), Decimal("NaN")):
            with self.assertRaises(SFCSerializationError):
                canonical_json_bytes({"x": bad})

    def test_normative_schemas_exist_and_forbid_hidden_composite_or_structural_leakage(self):
        names = ["representation_v0_1.schema.json", "comparison_v0_1.schema.json", "family_evidence_v0_1.schema.json", "replay_control_v0_1.schema.json"]
        loaded = {name: json.loads((SCHEMA_DIR / name).read_text()) for name in names}
        self.assertEqual(set(loaded), set(names))
        rep_text = json.dumps(loaded["representation_v0_1.schema.json"], sort_keys=True)
        self.assertIn("validation_label", rep_text)
        self.assertIn("family_id", rep_text)
        fam_text = json.dumps(loaded["family_evidence_v0_1.schema.json"], sort_keys=True)
        self.assertIn("composite_score", fam_text)
        self.assertIn("NO_STABLE_FAMILY", fam_text)

    def test_registries_keep_capability_noncanonical(self):
        cap = json.loads((REG_DIR / "SFC_CAPABILITY_REGISTRY.json").read_text())
        self.assertEqual(cap["production_representation_pack"], "NONE")
        self.assertEqual(cap["canonical_comparison_spec"], "NONE")
        self.assertEqual(cap["canonical_family_method"], "NONE")
        self.assertEqual(cap["canonical_family_catalog"], "NONE")
        reasons = json.loads((REG_DIR / "SFC_REASON_CODE_REGISTRY.json").read_text())
        self.assertIn("SFC_SRFD_JUNE_INTERLOCK_ACTIVE", reasons["codes"])
        self.assertIn("CAPACITY_EXCEEDED", reasons["missingness_statuses"])

    def test_frozen_v04_binding_is_exact_and_external(self):
        frozen = json.loads((REG_DIR / "SFC_FROZEN_RULEPACK_BINDINGS.json").read_text())
        row = frozen["bindings"][0]
        self.assertEqual(row["git_blob_sha"], "e4f5ce02a103000a48ed98e2110b8f1a7d497fcd")
        self.assertEqual(row["mutation"], "FORBIDDEN")
        self.assertEqual(frozen["sfc_generic_metric_contract"], "SEPARATE_FROM_SCIENTIFIC_RULEPACK")


if __name__ == "__main__":
    unittest.main()
