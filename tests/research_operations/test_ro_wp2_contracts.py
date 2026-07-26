from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ROWP2ContractsTests(unittest.TestCase):
    def test_required_wp2_outputs_exist(self) -> None:
        required = (
            "contracts/research_operations/RESEARCH_CLI_AND_APPEND_ONLY_SERVICE_CONTRACT_v0_1.md",
            "contracts/research_operations/ARTIFACT_CATALOGUE_AND_PATH_SAFETY_CONTRACT_v0_1.md",
            "schemas/research_operations/artifact_catalogue_v0_1.schema.json",
            "registries/research_operations/RESEARCH_OPERATIONS_COMMAND_REGISTRY_v0_1.json",
            "registries/research_operations/RESEARCH_OPERATIONS_PATH_REGISTRY_v0_1.json",
            "registries/research_operations/ARTIFACT_CATALOGUE_STATE_REGISTRY_v0_1.yaml",
            "fixtures/research_operations/ro_wp2/FIXTURE_PACK.json",
            "scripts/start_research_operations.ps1",
            "docs/research-operations/RO_WP2_WINDOWS_OPERATOR_GUIDE.md",
            "src/ovc/__main__.py",
            "src/ovc/research_operations/cli.py",
            "src/ovc/research_operations/catalogue.py",
            "src/ovc/research_operations/storage.py",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_path_registry_has_no_machine_paths_and_is_default_deny(self) -> None:
        registry = json.loads((ROOT / "registries/research_operations/RESEARCH_OPERATIONS_PATH_REGISTRY_v0_1.json").read_text())
        self.assertEqual("DENY", registry["default_policy"])
        self.assertFalse(registry["persist_absolute_paths"])
        self.assertFalse(registry["allow_symlinks"])
        text = json.dumps(registry)
        self.assertNotIn("C:\\", text)
        self.assertNotIn("/home/", text)

    def test_command_registry_has_no_network_or_git_authority(self) -> None:
        registry = json.loads((ROOT / "registries/research_operations/RESEARCH_OPERATIONS_COMMAND_REGISTRY_v0_1.json").read_text())
        self.assertEqual(12, len(registry["commands"]))
        self.assertEqual("APPROVED_BOUNDED_LOCAL_OPERATION_RO_G2_PASS", registry["status"])
        self.assertEqual("NONE", registry["network_operations"])
        self.assertEqual("NONE", registry["git_operations"])
        self.assertEqual("NONE", registry["r2_operations"])
        self.assertEqual("NONE", registry["market_classification"])

    def test_artifact_schema_uses_portable_locations(self) -> None:
        schema = json.loads((ROOT / "schemas/research_operations/artifact_catalogue_v0_1.schema.json").read_text())
        location = schema["$defs"]["PortableLocation"]
        self.assertEqual(["root_alias", "relative_path"], location["required"])
        self.assertFalse(location["additionalProperties"])

    def test_authority_is_wp2_reviewed_and_bounded_after_ro_g2(self) -> None:
        authority = (ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml").read_text()
        implementation = (ROOT / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text()
        self.assertIn("state: RO_G2_PASS_WP3_BUILD_AUTHORISED", authority)
        self.assertIn("ro_g2: PASS", authority)
        self.assertIn("cli: APPROVED_BOUNDED_LOCAL_OPERATION", authority)
        self.assertIn("artifact_catalogue: APPROVED_READ_VERIFY_REPORT_LOCAL", authority)
        self.assertIn("status: PASS_RO_WP3_BUILD_AUTHORISED", implementation)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
        for denied in ("active_research: NONE", "market_authority: NONE", "probability_authority: NONE", "exposure_authority: NONE", "execution_authority: NONE", "agent_authority: NONE"):
            self.assertIn(denied, authority)


if __name__ == "__main__":
    unittest.main()
