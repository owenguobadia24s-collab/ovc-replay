import json
from pathlib import Path
import unittest

from ovc.opt_b.esl.canonical import sha256_canonical
from ovc.opt_b.esl.soi_compat import adapt_family_catalog
from ovc.opt_b.sfc.fdi import FamilyMethodSpec, catalog_id
from ovc.opt_b.sfc.serialization import logical_hash

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "fixtures/opt_b/esl/wp6"
MANIFEST = ROOT / "registries/opt_b/esl/SOI_FAMILY_COMPATIBILITY_ADAPTER_MANIFEST_v0_1.json"


class ESLIWP6FixtureIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.present = json.loads((FIXTURE_ROOT / "family_catalog_present.json").read_text(encoding="utf-8"))
        cls.null_family = json.loads(
            (FIXTURE_ROOT / "family_catalog_no_stable_family.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def _expected_catalog_id(self, fixture: dict) -> str:
        method = FamilyMethodSpec(
            family_method_id=fixture["family_method_id"],
            method_version="0.1",
            configuration_id=fixture["configuration_id"],
            input_representation_pack_id=fixture["representation_pack_id"],
            comparison_spec_id=fixture["comparison_spec_id"],
        )
        return catalog_id(
            population_id=fixture["source_population_id"],
            representation_pack_id=fixture["representation_pack_id"],
            comparison_spec_id=fixture["comparison_spec_id"],
            method=method,
        )

    def test_wp6_14_distinct_source_configurations_have_distinct_catalog_identities(self):
        self.assertNotEqual(self.present["configuration_id"], self.null_family["configuration_id"])
        self.assertNotEqual(self.present["family_catalog_id"], self.null_family["family_catalog_id"])
        self.assertEqual(self.present["family_catalog_id"], self._expected_catalog_id(self.present))
        self.assertEqual(self.null_family["family_catalog_id"], self._expected_catalog_id(self.null_family))

    def test_wp6_15_source_and_projected_logical_hashes_are_independently_reproducible(self):
        for fixture in (self.present, self.null_family):
            with self.subTest(configuration=fixture["configuration_id"]):
                source_payload = dict(fixture)
                source_hash = source_payload.pop("logical_hash")
                self.assertEqual(source_hash, logical_hash(source_payload))

                result = adapt_family_catalog(fixture, adapter_manifest=self.manifest)
                projected_payload = {
                    key: value
                    for key, value in result.items()
                    if key not in {"soi_view_result_id", "logical_hash"}
                }
                self.assertEqual(result["logical_hash"], sha256_canonical(projected_payload))
                self.assertEqual(result["soi_view_result_id"], "soi1:" + result["logical_hash"])


if __name__ == "__main__":
    unittest.main()
