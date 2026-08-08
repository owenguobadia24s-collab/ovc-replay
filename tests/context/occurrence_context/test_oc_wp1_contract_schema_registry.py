import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas/context/occurrence_context"
REG = ROOT / "registries/context/occurrence_context"
FIX = ROOT / "fixtures/context/occurrence_context/v0_1"
CONTRACT = ROOT / "contracts/context/occurrence_context"


def canonical_hash(path: Path) -> str:
    payload = json.loads(path.read_text())
    expected = payload.pop("canonical_hash")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    actual = "sha256:" + hashlib.sha256(encoded).hexdigest()
    return expected, actual


class OCWP1ContractSchemaRegistryTests(unittest.TestCase):
    def test_required_contracts_and_schemas_exist(self):
        contracts = {
            "OCCURRENCE_CONTEXT_CONTRACT_v0_1.md",
            "OCCURRENCE_CONTEXT_CONSUMER_CONTRACT_v0_1.md",
            "OCCURRENCE_CONTEXT_STRUCTURAL_FIREWALL_v0_1.md",
            "OCCURRENCE_CONTEXT_CHRONOLOGY_CONTRACT_v0_1.md",
            "OCCURRENCE_CONTEXT_MC_ARB_REFERENCE_CONTRACT_v0_1.md",
        }
        self.assertTrue(all((CONTRACT / name).exists() for name in contracts))
        required = {
            "occurrence_context_v0_1.schema.json",
            "occurrence_anchor_ref_v0_1.schema.json",
            "context_dependency_ref_v0_1.schema.json",
            "context_role_map_v0_1.schema.json",
            "occurrence_context_supersession_v0_1.schema.json",
            "mcarb_context_ref_v0_1.schema.json",
            "occurrence_context_pack_v0_1.schema.json",
            "context_consumption_manifest_v0_1.schema.json",
            "market_condition_context_v0_1.schema.json",
        }
        for name in required:
            json.loads((SCHEMA / name).read_text())

    def test_base_schema_is_bounded_to_current_market_authority(self):
        schema = json.loads((SCHEMA / "occurrence_context_v0_1.schema.json").read_text())
        source = schema["properties"]["source_context"]["properties"]
        self.assertEqual(source["instrument_id"]["const"], "GBPUSD")
        self.assertEqual(source["price_side"]["enum"], ["BID", "ASK"])
        self.assertIn("VALIDATION_METADATA_ONLY", schema["properties"]["research_role"]["enum"])
        self.assertNotIn("ACTIVE", schema["properties"]["authority_state"]["enum"])

    def test_no_representation_input_or_scientific_admission(self):
        role = json.loads((REG / "CONTEXT_ROLE_MAP_v0_1.json").read_text())
        self.assertEqual(role["representation_admissions"], [])
        self.assertEqual(role["representation_input_status"], "DENIED_BY_DEFAULT")
        self.assertNotIn("REPRESENTATION_INPUT", set(role["field_roles"].values()))
        aux = json.loads((REG / "AUXILIARY_ADMISSION_REGISTRY_v0_1.json").read_text())
        self.assertEqual(aux["status"], "NO_SCIENTIFIC_ADMISSIONS")
        self.assertEqual(aux["admissions"], [])

    def test_session_and_market_condition_semantics_fail_closed(self):
        sessions = json.loads((REG / "CALENDAR_SESSION_BINDINGS_v0_1.json").read_text())
        self.assertEqual(sessions["status"], "NO_ACTIVE_SESSION_BOUNDARY_DEFINITION")
        self.assertEqual(sessions["session_membership_definitions"], [])
        self.assertEqual(sessions["a_l_membership_definitions"], [])
        self.assertTrue(sessions["invention_prohibited"])
        market = json.loads((REG / "MARKET_CONDITION_VOCABULARY_BINDINGS_v0_1.json").read_text())
        self.assertEqual(market["status"], "NO_ACTIVE_VOCABULARY")
        self.assertEqual(market["vocabularies"], [])

    def test_registry_hashes_are_reproducible(self):
        for name in (
            "CONTEXT_ROLE_MAP_v0_1.json",
            "OCCURRENCE_CONTEXT_PACK_REGISTRY_v0_1.json",
            "CALENDAR_SESSION_BINDINGS_v0_1.json",
            "MARKET_CONDITION_VOCABULARY_BINDINGS_v0_1.json",
            "AUXILIARY_ADMISSION_REGISTRY_v0_1.json",
            "REASON_CODE_REGISTRY_v0_1.json",
            "AUTHORITY_STATE_REGISTRY_v0_1.json",
        ):
            expected, actual = canonical_hash(REG / name)
            self.assertEqual(expected, actual, name)

    def test_pack_forbids_outcome_and_validation_payload(self):
        pack = json.loads((REG / "OCCURRENCE_CONTEXT_PACK_REGISTRY_v0_1.json").read_text())["entries"][0]
        forbidden = set(pack["prohibited_fields"])
        self.assertTrue({"outcome", "future_return", "probability", "risk", "exposure", "execution", "validation_occurrence_payload"}.issubset(forbidden))

    def test_fixture_catalogue_is_complete(self):
        catalogue = json.loads((FIX / "adversarial/OC_ADVERSARIAL_FIXTURE_CATALOGUE_v0_1.json").read_text())
        self.assertEqual([f"OC-F{i:02d}" for i in range(1, 17)], [item["fixture_id"] for item in catalogue["fixtures"]])
        golden = json.loads((FIX / "golden/OC_GOLDEN_CONTEXT_001.json").read_text())
        self.assertEqual(golden["source_context"]["instrument_id"], "GBPUSD")
        self.assertEqual(golden["session_context"]["status"], "UNAVAILABLE")
        self.assertEqual(golden["availability"]["status"], "PARTIAL")
        self.assertIn("OC_SESSION_UNRESOLVED", golden["reason_codes"])


if __name__ == "__main__":
    unittest.main()
