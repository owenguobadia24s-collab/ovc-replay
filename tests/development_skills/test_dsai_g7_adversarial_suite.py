from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import unittest

from ovc.development.skills import (
    BaseFreshnessPolicy,
    audit_evidence,
    build_tool_request,
    decide_tool_request,
    resolve_security_envelope,
    sandbox_leakage_probe,
    shadow_authority_resolver,
    shadow_preflight,
    shadow_prerequisite_resolver,
    shadow_scope_guard,
)

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "fixtures/development_skills/g7_adversarial_suite_v0_1.json"
MANDATORY = {
    "AUTHORITY_CONFUSION",
    "SCOPE_EXPANSION",
    "MISSING_PREREQUISITE",
    "SOURCE_PRECEDENCE",
    "STALE_APPROVAL",
    "VALIDATION_LEAKAGE",
    "PERMISSION_ESCALATION",
}


def _run_case(case: dict) -> tuple[str, list[str]]:
    driver = case["driver"]
    payload = case["input"]

    if driver == "authority_resolver":
        row = shadow_authority_resolver(**payload)
        return row["disposition"], row["reason_codes"]

    if driver == "scope_guard":
        try:
            row = shadow_scope_guard(**payload)
        except (ValueError, OSError):
            return "ERROR_FAIL_CLOSED", []
        return row["disposition"], row["reason_codes"]

    if driver == "prerequisite_resolver":
        row = shadow_prerequisite_resolver(**payload)
        return row["disposition"], row["reason_codes"]

    if driver == "preflight":
        row = shadow_preflight(payload)
        return row["disposition"], row["reason_codes"]

    if driver == "freshness":
        row = BaseFreshnessPolicy().assess(**payload)
        observed = "PASS" if row["status"] == "FRESH" else "BLOCK"
        return observed, row["reason_codes"]

    if driver == "evidence_audit":
        row = audit_evidence(payload["records"])
        return row["status"], row["reason_codes"]

    if driver == "security":
        env_args = {
            "skill_id": "OVC-SKILL-G7-ADVERSARIAL",
            "capability_ids": ["G7_ADVERSARIAL_EXECUTION"],
            "allowed_semantic_actions": payload["envelope"].get("allowed_semantic_actions", []),
            "read_prefixes": payload["envelope"].get("read_prefixes", []),
            "write_prefixes": payload["envelope"].get("write_prefixes", []),
            "semantic_owners": payload["envelope"].get("semantic_owners", []),
            "logical_credential_ids": payload["envelope"].get("logical_credential_ids", []),
            "network_allowlist": payload["envelope"].get("network_allowlist", []),
            "write_authority_active": payload["envelope"].get("write_authority_active", False),
            "validation_authority_active": payload["envelope"].get("validation_authority_active", False),
        }
        envelope = resolve_security_envelope(**env_args)
        request = build_tool_request(**payload["request"])
        row = decide_tool_request(envelope, request)
        observed = "PASS" if row["decision"] == "ALLOW" else "BLOCK"
        return observed, row["reason_codes"]

    if driver == "sandbox":
        row = sandbox_leakage_probe(**payload)
        return row["status"], []

    raise AssertionError(f"unknown driver {driver}")


class DSAIG7AdversarialSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))

    def test_suite_is_seven_families_six_cases_each_and_non_authoritative(self):
        self.assertEqual(self.suite["authority_effect"], "NONE")
        self.assertEqual(self.suite["qualification_effect"], "NONE_UNTIL_INDEPENDENT_HUMAN_REVIEW_ACCEPTED")
        self.assertEqual(self.suite["author_role"], "AI_ASSISTED_ADVERSARIAL_CURATOR")
        self.assertEqual(self.suite["independent_human_review_state"], "PENDING")
        self.assertEqual(set(self.suite["families"]), MANDATORY)
        counts = Counter(row["family"] for row in self.suite["cases"])
        self.assertEqual(set(counts), MANDATORY)
        self.assertEqual(set(counts.values()), {6})
        self.assertEqual(self.suite["case_count"], 42)
        self.assertEqual(len(self.suite["cases"]), 42)

    def test_all_adversarial_cases_match_expected_disposition_and_reason(self):
        for case in self.suite["cases"]:
            with self.subTest(case_id=case["case_id"], family=case["family"]):
                observed, reasons = _run_case(case)
                self.assertEqual(observed, case["expected"], case)
                expected_reason = case.get("expected_reason")
                if expected_reason:
                    self.assertIn(expected_reason, reasons, case)

    def test_suite_does_not_fabricate_independent_human_review(self):
        self.assertEqual(self.suite["independent_human_review_state"], "PENDING")
        self.assertNotEqual(self.suite["author_role"], "INDEPENDENT_HUMAN_REVIEWER")
        self.assertEqual(self.suite["authority_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
