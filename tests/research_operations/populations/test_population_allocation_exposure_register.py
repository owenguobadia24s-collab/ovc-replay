import json
from pathlib import Path
import unittest

from ovc.research_operations.population_registry import (
    PopulationRegisterError,
    append_exposure_event,
    eligibility,
    make_exposure_event,
    validate_register,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registries" / "research_operations" / "populations" / "OVC_POPULATION_ALLOCATION_EXPOSURE_REGISTER_v0_1.json"


class TestPopulationAllocationExposureRegister(unittest.TestCase):
    def setUp(self):
        self.register = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_seed_is_exact_32_populations_64_clock_views(self):
        validate_register(self.register)
        self.assertEqual(self.register["population_count"], 32)
        self.assertEqual(self.register["clock_view_count"], 64)

    def test_population_identity_is_not_clock_identity(self):
        pop = next(p for p in self.register["populations"] if p["instrument"] == "GBPUSD" and p["partition_id"] == "P4")
        self.assertEqual({v["clock"] for v in pop["clock_views"]}, {"15M", "120M"})

    def test_metadata_only_never_manufactures_development_authority(self):
        pop = self.register["populations"][0]
        event = make_exposure_event(
            population_id=pop["population_id"], programme_id="TEST", study_id="S1",
            research_role="DISCOVERY", exposure_kind="METADATA_ONLY",
            occurred_at="2026-09-22T18:00:00+01:00",
        )
        updated = append_exposure_event(self.register, event)
        self.assertEqual(eligibility(updated, pop["population_id"], "DEVELOPMENT")["status"], "UNKNOWN_PENDING_OPERATOR_AND_OWNER_PREFLIGHT")

    def test_substantive_exposure_forces_reconciliation(self):
        pop = self.register["populations"][0]
        event = make_exposure_event(
            population_id=pop["population_id"], programme_id="TEST", study_id="S1",
            research_role="DISCOVERY", exposure_kind="PAYLOAD_READ",
            occurred_at="2026-09-22T18:00:00+01:00",
        )
        updated = append_exposure_event(self.register, event)
        self.assertEqual(eligibility(updated, pop["population_id"], "DEVELOPMENT")["status"], "EXPOSURE_RECONCILIATION_REQUIRED")

    def test_validation_remains_separate_reserved_authority(self):
        pop = self.register["populations"][0]
        self.assertTrue(eligibility(self.register, pop["population_id"], "VALIDATION")["status"].startswith("LOCKED_"))

    def test_event_cannot_grant_authority(self):
        pop = self.register["populations"][0]
        event = make_exposure_event(
            population_id=pop["population_id"], programme_id="TEST", study_id="S1",
            research_role="DISCOVERY", exposure_kind="PAYLOAD_READ", occurred_at="x",
        )
        event["authority_effect"] = "ACTIVE"
        bad = dict(self.register)
        bad["exposure_events"] = [event]
        with self.assertRaises(PopulationRegisterError):
            validate_register(bad)


if __name__ == "__main__":
    unittest.main()
