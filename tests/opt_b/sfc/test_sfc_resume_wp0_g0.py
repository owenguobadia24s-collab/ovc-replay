import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "registries/implementation/sfc/OVC_SFC_STATE_v0_3.json"
POINTER = ROOT / "registries/implementation/sfc/CURRENT_STATE_POINTER.json"
OLD_STATE = ROOT / "registries/implementation/sfc/OVC_SFC_STATE_v0_2.json"
BASE = ROOT / "docs/releases/sri-fdi-conformance-v0-1"
PREFLIGHT = BASE / "sfc-wp0-resume/SFC_WP0_FRESH_PREFLIGHT_RECORD.json"
SURVEY = BASE / "sfc-wp0-resume/SFC_WP0_SEMANTIC_COMPATIBILITY_SURVEY.json"
DEPENDENCY = BASE / "sfc-wp0-resume/SFC_WP0_UPSTREAM_DEPENDENCY_RECORD.json"
INTERLOCK = BASE / "sfc-wp0-resume/SFC_WP0_JUNE_INTERLOCK_RECORD.json"
DECISION = BASE / "sfc-g0-resume/SFC_G0_RESUME_OPERATOR_DECISION.json"
DELEGATION = BASE / "sfc-g0-resume/SFC_G0_STANDING_OPERATOR_DELEGATION.json"

class SFCResumeWP0G0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.old = json.loads(OLD_STATE.read_text())
        cls.preflight = json.loads(PREFLIGHT.read_text())
        cls.survey = json.loads(SURVEY.read_text())
        cls.dep = json.loads(DEPENDENCY.read_text())
        cls.interlock = json.loads(INTERLOCK.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.delegation = json.loads(DELEGATION.read_text())

    def test_prior_defer_is_immutable_and_resume_is_append_only(self):
        self.assertEqual(self.old["programme_disposition"], "DEFERRED")
        self.assertEqual(self.state["programme_disposition"], "RESUMED_FROM_DEFER")
        self.assertIn("SFC-G0.OPERATOR.DEFER", self.state["operator_decision_history"])
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertTrue(self.decision["preserves_historical_defer"])

    def test_fresh_wp0_is_pinned_and_upstream_is_ready_without_activation(self):
        self.assertEqual(self.preflight["checked_main"], "682fdbf6893d37446926011d461157fbce5cf8f2")
        self.assertEqual(self.dep["dependency_readiness"], "READY")
        self.assertEqual(self.dep["active_c2e"], "NONE")
        self.assertEqual(self.dep["real_source_replay"], "DENIED_DEFERRED_AT_C2E2_G6")
        self.assertEqual(self.dep["missing_or_incompatible_artifacts"], [])

    def test_semantic_survey_excludes_legacy_and_forbidden_normative_inputs(self):
        self.assertEqual(self.survey["result"], "PASS_NO_ABSENT_REQUIRED_FIELDS")
        self.assertEqual(self.survey["field_classes"]["ABSENT_REQUIRED"], [])
        self.assertTrue(any("QUALITY" in x for x in self.survey["field_classes"]["LEGACY_ONLY"]))
        self.assertTrue(any("family_id" in x for x in self.survey["field_classes"]["FORBIDDEN"]))
        self.assertEqual(self.survey["no_fallback"], "HISTORICAL_MG_C2E_V0_1_FORBIDDEN_AS_NORMATIVE_SOURCE")

    def test_frozen_science_and_interlock_are_exact(self):
        frozen = self.state["frozen_science"]
        self.assertEqual(frozen["git_blob_sha"], "e4f5ce02a103000a48ed98e2110b8f1a7d497fcd")
        self.assertEqual(frozen["logical_sha256"], "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b")
        self.assertEqual(self.interlock["srfd_june_authority_interlock"], "DENY")
        self.assertEqual(self.interlock["failure_reason"], "SFC_SRFD_JUNE_INTERLOCK_ACTIVE")
        self.assertEqual(self.pointer["srfd_june_authority_interlock"], "DENY")

    def test_standing_delegation_never_grants_reserved_authority(self):
        self.assertIn("NO_JUNE_SCIENTIFIC_RUN_AUTHORITY", self.delegation["hard_limits"])
        self.assertIn("NO_SELECTOR_MUTATION", self.delegation["hard_limits"])
        self.assertIn("NO_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION_OR_AGENT_WRITE_AUTHORITY", self.delegation["hard_limits"])
        self.assertEqual(self.state["authority"]["validation_2025"], "LOCKED_UNCONSUMED")
        self.assertEqual(self.state["authority"]["selector_family_semantic_publication"], "NONE")

if __name__ == "__main__":
    unittest.main()
