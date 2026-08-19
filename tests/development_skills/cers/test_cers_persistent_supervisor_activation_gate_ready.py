from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATE_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/activation/"
    "CERS_G_PERSISTENT_SUPERVISOR_ACTIVATION_GATE_PACKET_v0_1.json"
)
QA_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/activation/"
    "CERS_G_PERSISTENT_SUPERVISOR_ACTIVATION_GATE_READY_QA_v0_1.json"
)
TARGET_QUALIFICATION_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/wp5/"
    "CERS_PS_WP5_TARGET_RUNTIME_QUALIFICATION_v0_1.json"
)
HISTORICAL_STATE_PATH = (
    ROOT
    / "registries/implementation/dsai3v_cers_v0_1/"
    "OVC_DSAI3V_CERS_STATE_v0_16.json"
)


def load(relative: str | Path):
    path = relative if isinstance(relative, Path) else ROOT / relative
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


class CersPersistentSupervisorActivationGateReadyTests(unittest.TestCase):
    def setUp(self):
        self.gate = load(GATE_PATH)
        self.qa = load(QA_PATH)
        self.target = load(TARGET_QUALIFICATION_PATH)
        self.state = load(HISTORICAL_STATE_PATH)

    def test_gate_ready_artifact_remains_immutable_historical_evidence(self):
        self.assertEqual(self.gate["status"], "GATE_READY")
        self.assertEqual(self.gate["decision"], "PENDING_OPERATOR")
        self.assertEqual(self.gate["authority_required"], "OPERATOR_REQUIRED")
        self.assertEqual(self.gate["persistent_run"], "NOT_ACTIVATED")
        self.assertEqual(
            self.gate["terminal_instruction"],
            "STOP_WITHOUT_RUN_AND_AWAIT_OPERATOR_DECISION",
        )
        self.assertFalse(
            self.gate["exact_proposed_activation_delta"]["automatic_activation_from_this_packet"]
        )
        self.assertEqual(self.state["decision"], "PENDING_OPERATOR")
        self.assertEqual(
            self.state["persistent_general_dispatch"],
            "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
        )

    def test_target_executor_runtime_family_is_exactly_qualified(self):
        self.assertEqual(self.target["status"], "PASS")
        self.assertEqual(self.target["executor_environment_binding"], "windows-local-python311")
        self.assertEqual(self.target["environment"]["python_family"], "3.11")
        self.assertEqual(self.target["environment"]["python"], "3.11.9")
        self.assertEqual(self.target["qualification"]["iterations"], 1000)
        self.assertEqual(set(self.target["qualification"]["assertions"].values()), {"PASS"})
        self.assertEqual(self.target["qualification"]["blocking_warnings"], [])
        self.assertEqual(self.target["qualification"]["incidents"], [])
        self.assertEqual(
            sha256(TARGET_QUALIFICATION_PATH),
            self.gate["runtime"]["target_runtime_qualification_sha256"],
        )

    def test_gate_referenced_runtime_and_registry_blobs_remain_exact(self):
        artifact_records = self.gate["runtime"]["artifacts"] + [
            {
                "path": self.gate["admission"]["registry"],
                "git_blob": self.gate["admission"]["registry_git_blob"],
            },
            {
                "path": self.gate["packet_executor"]["binding_record"],
                "git_blob": self.gate["packet_executor"]["binding_git_blob"],
            },
            {
                "path": self.gate["actions_and_side_effects"]["registry"],
                "git_blob": self.gate["actions_and_side_effects"]["registry_git_blob"],
            },
        ]
        for record in artifact_records:
            self.assertEqual(git_blob(ROOT / record["path"]), record["git_blob"])

    def test_gate_qa_is_content_addressed_and_has_no_blocker(self):
        self.assertEqual(sha256(GATE_PATH), self.qa["gate_packet_sha256"])
        self.assertEqual(self.qa["status"], "PASS_GATE_READY")
        self.assertEqual(set(self.qa["checks"].values()), {"PASS"})
        self.assertEqual(self.qa["blockers"], [])
        self.assertEqual(self.qa["incidents"], [])

    def test_reserved_authority_was_explicitly_unchanged_at_gate_ready(self):
        unchanged = self.gate["exact_proposed_activation_delta"]["does_not_change"]
        joined = " ".join(unchanged)
        for reserved in (
            "Programme authority", "Future programme admission", "Direct-main",
            "ACTIVE_DISCOVERY", "Scientific", "publication", "Validation",
            "risk", "trading", "market-execution", "Irreversible",
        ):
            self.assertIn(reserved, joined)
        self.assertTrue(self.state["reserved_authority_unchanged"])


if __name__ == "__main__":
    unittest.main()
