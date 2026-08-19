from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CersPersistentSupervisorActivationTests(unittest.TestCase):
    def setUp(self):
        self.pointer = load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
        self.state = load(self.pointer["current_state"])
        self.decision = load(
            "docs/releases/development-skills-v0-3/cers-persistent-supervisor/activation/"
            "CERS_G_PERSISTENT_SUPERVISOR_ACTIVATION_OPERATOR_DECISION_v0_1.json"
        )
        self.admission = load(self.state["admission_registry"])
        self.quiescence = load(self.state["quiescence_state"])

    def test_operator_pass_is_exact_and_current(self):
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(
            self.decision["operator_phrase"],
            "OVC APPROVE CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION PASS",
        )
        self.assertEqual(self.pointer["decision"], "PASS")
        self.assertEqual(self.state["decision_authority"], "OPERATOR")

    def test_persistent_run_is_active_only_for_explicit_admitted_scope(self):
        self.assertEqual(self.pointer["persistent_run"], "ACTIVATED")
        self.assertEqual(self.state["persistent_run"], "ACTIVATED")
        self.assertEqual(self.quiescence["mode"], "RUN")
        self.assertEqual(self.admission["status"], "ACTIVE_PERSISTENT")
        self.assertFalse(self.admission["future_programme_auto_admission"])
        self.assertEqual(len(self.admission["entries"]), 1)
        self.assertEqual(
            self.admission["entries"][0]["programme_id"],
            "OVC-DSAI3V-CERS-CONFORMANCE-v0.1",
        )

    def test_physical_and_reserved_authority_did_not_expand(self):
        self.assertFalse(self.state["parallel_physical_merge"])
        self.assertEqual(self.state["controller_identity"], "DSAI_VIT_PHYSICAL_CONTROLLER")
        self.assertEqual(self.state["physical_gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")
        self.assertTrue(self.state["reserved_authority_unchanged"])
        preserved = " ".join(self.decision["preserved_boundaries"])
        for token in (
            "NO_PROGRAMME_AUTHORITY_INFERENCE",
            "NO_FUTURE_PROGRAMME_AUTO_ADMISSION",
            "NO_DIRECT_MAIN_MUTATION",
            "NO_CERS_MERGE_CAPABILITY",
            "NO_FORCE_PUSH_OR_HISTORY_REWRITE",
            "NO_ACTIVE_DISCOVERY_DEVELOPMENT_VALIDATION_GRANT",
            "NO_SCIENTIFIC_OR_SEMANTIC_PROMOTION",
            "NO_VALIDATION_CONSUMPTION",
            "NO_PROBABILITY_RISK_EXPOSURE_TRADING_OR_MARKET_EXECUTION",
        ):
            self.assertIn(token, preserved)

    def test_grt_remains_outside_activated_admission(self):
        grt = [
            x for x in self.admission["exclusions"]
            if x["programme_id"] == "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"
        ]
        self.assertEqual(len(grt), 1)
        self.assertIn("NOT_IN_ACTIVATED_ADMISSION_SET", grt[0]["reason_codes"])


if __name__ == "__main__":
    unittest.main()
