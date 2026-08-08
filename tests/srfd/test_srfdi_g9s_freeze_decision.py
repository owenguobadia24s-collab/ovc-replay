from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFDI_G9S_FREEZE_OPERATOR_DECISION.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_2.json"
PACKS = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"
MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9s/SRFD_JUNE_RUN_MANIFEST_TEMPLATE_v0_2.json"


class SRFDIG9SFreezeDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.packs = json.loads(PACKS.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())

    def test_operator_command_and_decision_are_exact(self) -> None:
        self.assertEqual("SRFDI-G9S-FREEZE", self.decision["gate_id"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual(
            "OVC APPROVE SRFDI-G9S-FREEZE PREREGISTRATION_FREEZE",
            self.decision["operator_command"],
        )

    def test_exact_candidate_hashes_are_frozen(self) -> None:
        candidate = self.decision["approved_candidate"]
        self.assertEqual(
            "13c17cf64c576b35e53047de753a5fd1a49bbdc7205c387bbcedb5a34441b804",
            candidate["preregistration_v0_2_byte_sha256"],
        )
        self.assertEqual(
            "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0",
            candidate["representation_pack_registry_v0_2_byte_sha256"],
        )
        self.assertEqual(
            "6dd9a0e12ce01bf22e25d7ea499e1b16b7a9a02c6ed2733d132ef556c64ec41e",
            candidate["run_manifest_template_v0_2_byte_sha256"],
        )

    def test_authority_delta_is_freeze_only_and_june_remains_denied(self) -> None:
        effect = self.decision["authority_effect"]
        self.assertEqual("FROZEN_EXACT_VERSION", effect["preregistration_v0_2"])
        self.assertEqual("FROZEN_AS_PART_OF_PREREGISTRATION", effect["representation_pack_registry_v0_2"])
        self.assertEqual("DENIED_PENDING_SEPARATE_SRFDI_G_JUNE_AUTH", effect["june_execution"])
        self.assertEqual("DENIED", effect["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", effect["validation_2025"])
        self.assertEqual("NONE", effect["selector_change"])
        self.assertEqual("NONE", effect["scientific_promotion"])
        self.assertEqual("NONE", effect["publication"])
        self.assertEqual("NONE", effect["probability_risk_exposure_execution"])
        self.assertEqual("DENIED", self.manifest["run_authority"])

    def test_unavailable_packs_remain_explicit(self) -> None:
        rows = {row["implementation_class_id"]: row for row in self.packs["representation_packs"]}
        for pack_id in ("SRFDI-R2", "SRFDI-R3", "SRFDI-R4", "SRFDI-R5", "SRFDI-R7"):
            self.assertEqual("DEPENDENCY_UNAVAILABLE", rows[pack_id]["availability"])
        for pack_id in ("SRFDI-R1", "SRFDI-R6", "SRFDI-R8", "SRFDI-R9"):
            self.assertEqual("AVAILABLE_PREBENCHMARK", rows[pack_id]["availability"])


if __name__ == "__main__":
    unittest.main()
