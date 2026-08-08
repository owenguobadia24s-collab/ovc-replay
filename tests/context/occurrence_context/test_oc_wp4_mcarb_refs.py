import json
from pathlib import Path
import unittest

from ovc.context.occurrence_context.builder import OccurrenceContextError
from ovc.context.occurrence_context.mcarb_refs import build_mcarb_context_ref

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registries/context/occurrence_context/AUXILIARY_ADMISSION_REGISTRY_v0_1.json"


def payload(kind="ACTIVITY_LIQUIDITY"):
    return {
        "kind": kind,
        "record_id": "MCARB.FIXTURE.001",
        "record_schema_id": "mcarb_fixture/v1",
        "record_logical_hash": "sha256:mcarb-fixture-001",
        "domain_id": "FIXTURE.DOMAIN",
        "candidate_or_pack_id": "MCARB.FIXTURE.PACK",
        "candidate_or_pack_version": "0.1",
        "source_release_id": "FIXTURE.RELEASE",
        "source_record_ids": ["S2", "S1", "S1"],
        "first_valid_time": "2026-01-01T00:15:00Z",
        "availability_status": "AVAILABLE",
        "qualification_record_id": "QUAL.FIXTURE.001",
        "qualification_status": "FIXTURE_ONLY",
    }


class OCWP4MCARBReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text())

    def test_production_ref_is_denied_when_registry_has_no_scientific_admissions(self):
        self.assertEqual(self.registry["status"], "NO_SCIENTIFIC_ADMISSIONS")
        with self.assertRaises(OccurrenceContextError) as caught:
            build_mcarb_context_ref(payload(), self.registry)
        self.assertEqual(caught.exception.reason_code, "OC_MCARB_NOT_ADMITTED")

    def test_fixture_ref_is_typed_deterministic_and_inert(self):
        first = build_mcarb_context_ref(payload(), self.registry, fixture_only=True)
        second = build_mcarb_context_ref(payload(), self.registry, fixture_only=True)
        self.assertEqual(first, second)
        self.assertEqual(first["authority_effect"], "NONE")
        self.assertEqual(first["context_admission_id"], "OC.AUXILIARY.FIXTURE_ONLY.v0.1")
        self.assertEqual(first["source_record_ids"], ["S1", "S2"])

    def test_all_registered_fixture_categories_are_supported(self):
        for kind in self.registry["fixture_only_categories"]:
            ref = build_mcarb_context_ref(payload(kind), self.registry, fixture_only=True)
            self.assertEqual(ref["kind"], kind)

    def test_vectors_embeddings_and_feature_maps_are_blocked(self):
        for key, value in (
            ("vector", [1, 2]),
            ("embedding", [1, 2]),
            ("features", {"x": "1"}),
            ("normalized_features", {"x": "1"}),
        ):
            candidate = payload()
            candidate[key] = value
            with self.assertRaises(OccurrenceContextError) as caught:
                build_mcarb_context_ref(candidate, self.registry, fixture_only=True)
            self.assertEqual(caught.exception.reason_code, "OC_MCARB_NOT_ADMITTED")

    def test_fixture_descriptor_must_be_compact_scalars(self):
        candidate = payload("PROVIDER_SOURCE_CHARACTERISTIC")
        candidate["compact_descriptor"] = {"provider": "DUKASCOPY", "quality": "FIXTURE"}
        ref = build_mcarb_context_ref(candidate, self.registry, fixture_only=True)
        self.assertEqual(ref["compact_descriptor"]["provider"], "DUKASCOPY")
        candidate["compact_descriptor"] = {"nested": {"bad": True}}
        with self.assertRaises(OccurrenceContextError):
            build_mcarb_context_ref(candidate, self.registry, fixture_only=True)

    def test_required_identity_version_hash_and_fvt_fields_fail_closed(self):
        for field in ("record_id", "record_schema_id", "record_logical_hash", "candidate_or_pack_id", "candidate_or_pack_version", "first_valid_time", "qualification_record_id"):
            candidate = payload()
            candidate[field] = ""
            with self.assertRaises(OccurrenceContextError) as caught:
                build_mcarb_context_ref(candidate, self.registry, fixture_only=True)
            self.assertEqual(caught.exception.reason_code, "OC_MCARB_REF_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
