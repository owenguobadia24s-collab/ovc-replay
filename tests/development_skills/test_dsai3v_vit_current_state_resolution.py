from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.development.skills.vit_current_state import (
    VitCurrentStateResolutionError,
    classify_vit_status_source,
    resolve_current_vit_query,
)

ROOT = Path(__file__).resolve().parents[2]


def _write_json(root: Path, relative: str, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(root: Path, *, include_pointer: bool = True, substrate_authority_id: str = "AUTH-1") -> None:
    if include_pointer:
        _write_json(
            root,
            "registries/implementation/dsai_vit_v0_3/CURRENT_STATE_POINTER.json",
            {
                "schema": "ovc-programme-current-state-pointer/v1",
                "programme_id": "OVC-DSAI-VIT-v0.3",
                "current_state": "OVC_DSAI_VIT_V0_3_STATE_v0_19.json",
                "status": "COMPLETED",
            },
        )
    _write_json(
        root,
        "registries/implementation/dsai_vit_v0_3/OVC_DSAI_VIT_V0_3_STATE_v0_19.json",
        {
            "programme_id": "OVC-DSAI-VIT-v0.3",
            "status": "COMPLETED",
            "qualification_frontier": "GENERAL_VIT_STABILIZED",
            "current_qualification_stage": "TERMINAL",
            "general_authority": "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json",
            "current_authority": {
                "vit_live_physical_main_control": "ACTIVE_GENERAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION",
                "routing_scope": "NORMAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION",
            },
        },
    )
    _write_json(
        root,
        "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json",
        {
            "authority_id": "AUTH-1",
            "programme_id": "OVC-DSAI-VIT-v0.3",
            "authority_status": "ACTIVE",
            "routing_scope": "NORMAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION",
            "controller": "DSAI_VIT_PHYSICAL_CONTROLLER",
            "physical_gateway": "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
            "serialization": {"parallel_physical_merge": False},
        },
    )
    _write_json(
        root,
        "registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json",
        {
            "status": "ACTIVE",
            "substrate_id": substrate_authority_id,
            "source_authority": "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json",
            "controller": "DSAI_VIT_PHYSICAL_CONTROLLER",
            "execution_policy": {"physical_gateway": "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"},
        },
    )
    _write_json(
        root,
        "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-g-vit-pilot/DSAI3V_G_VIT_PILOT_GATE_READY.json",
        {
            "gate_status": "GATE_READY",
            "vit_live_physical_main_control": "DENIED",
        },
    )


class Dsai3vVitCurrentStateResolutionTests(unittest.TestCase):
    def test_real_repository_resolves_current_general_active_state(self) -> None:
        result = resolve_current_vit_query(ROOT)
        self.assertEqual(result["resolution_status"], "RESOLVED_CURRENT")
        self.assertEqual(result["programme_status"], "COMPLETED")
        self.assertEqual(result["general_authority_status"], "ACTIVE")
        self.assertEqual(result["default_execution_substrate_status"], "ACTIVE")
        self.assertTrue(result["vit_live_physical_main_control"].startswith("ACTIVE_"))
        self.assertFalse(result["historical_source_fallback_allowed"])

    def test_historical_pilot_gate_is_never_current_status_authority(self) -> None:
        historical = "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-g-vit-pilot/DSAI3V_G_VIT_PILOT_GATE_READY.json"
        self.assertEqual(classify_vit_status_source(historical), "HISTORICAL_EVIDENCE_NOT_CURRENT_STATUS")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root)
            result = resolve_current_vit_query(root)
            self.assertEqual(result["general_authority_status"], "ACTIVE")
            self.assertTrue(result["vit_live_physical_main_control"].startswith("ACTIVE_"))

    def test_missing_current_pointer_fails_closed_instead_of_falling_back_to_old_gate(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root, include_pointer=False)
            with self.assertRaisesRegex(VitCurrentStateResolutionError, "VIT_CURRENT_SOURCE_MISSING"):
                resolve_current_vit_query(root)

    def test_substrate_authority_identity_mismatch_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root, substrate_authority_id="AUTH-OLD")
            with self.assertRaisesRegex(VitCurrentStateResolutionError, "VIT_CURRENT_SUBSTRATE_AUTHORITY_ID_MISMATCH"):
                resolve_current_vit_query(root)

    def test_plan_and_design_sources_are_never_current_status_authority(self) -> None:
        self.assertEqual(
            classify_vit_status_source("docs/plans/development-skills-v0-3/vit/plan.md"),
            "HISTORICAL_OR_DESIGN_EVIDENCE_NOT_CURRENT_STATUS",
        )
        self.assertEqual(
            classify_vit_status_source("docs/design/development-skills-v0-3/vit/design.md"),
            "HISTORICAL_OR_DESIGN_EVIDENCE_NOT_CURRENT_STATUS",
        )


if __name__ == "__main__":
    unittest.main()
