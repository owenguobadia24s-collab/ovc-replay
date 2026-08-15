from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.programme_state_preflight import run_programme_state_preflight


class ProgrammeStatePreflightTests(unittest.TestCase):
    def _write(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def _fixture(self, root: Path, *, pointer_overrides: dict | None = None, state_overrides: dict | None = None) -> None:
        state = {
            "schema": "ovc-programme-state/v1",
            "programme_id": "P",
            "status": "COMPLETED",
            "packet_id": "P-WP1",
            "gate_id": "P-G1",
            "next_packet": "P-WP2",
            "completed_packets": ["P-WP1"],
        }
        state.update(state_overrides or {})
        pointer = {
            "schema": "ovc-programme-current-state-pointer/v1",
            "programme_id": "P",
            "current_state": "STATE.json",
            "status": "COMPLETED",
            "current_packet": "P-WP1",
            "current_gate": "P-G1",
            "next_packet": "P-WP2",
        }
        pointer.update(pointer_overrides or {})
        base = root / "registries/implementation/p"
        self._write(base / "STATE.json", state)
        self._write(base / "CURRENT_STATE_POINTER.json", pointer)

    def test_consistent_pointer_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            receipt = run_programme_state_preflight(root)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["blocking_count"], 0)
            self.assertEqual(receipt["checks"][0]["reason"], "POINTER_STATE_CONSISTENT")

    def test_stale_current_packet_blocks_before_expensive_assurance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, pointer_overrides={"current_packet": "P-WP0"})
            receipt = run_programme_state_preflight(root)
            self.assertEqual(receipt["status"], "BLOCK")
            self.assertIn("POINTER_STATE_FIELD_MISMATCH", {row["reason"] for row in receipt["checks"]})

    def test_successor_already_completed_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, state_overrides={"completed_packets": ["P-WP1", "P-WP2"]})
            receipt = run_programme_state_preflight(root)
            self.assertEqual(receipt["status"], "BLOCK")
            self.assertIn("NEXT_PACKET_ALREADY_COMPLETED", {row["reason"] for row in receipt["checks"]})

    def test_missing_referenced_state_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, pointer_overrides={"current_state": "MISSING.json"})
            receipt = run_programme_state_preflight(root)
            self.assertEqual(receipt["status"], "BLOCK")
            self.assertEqual(receipt["checks"][0]["reason"], "CURRENT_STATE_NOT_FOUND")

    def test_noncanonical_pointer_schema_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, pointer_overrides={"schema": "legacy-pointer/v0"})
            receipt = run_programme_state_preflight(root)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["checks"][0]["reason"], "NON_CANONICAL_POINTER_SCHEMA_SKIPPED")


if __name__ == "__main__":
    unittest.main()
