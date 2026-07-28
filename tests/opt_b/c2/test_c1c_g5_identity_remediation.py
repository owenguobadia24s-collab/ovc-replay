from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/opt_b/run_c1c_g5_c2_remediation.py"
SPEC = importlib.util.spec_from_file_location("c1c_g5_remediation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class C1CG5IdentityRemediationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.row = {
            "axes": {
                "INTERACTION": {"reason_code": "NO_FIRST_VALID_LEVEL", "status": "NOT_EVALUATED", "value": None},
                "LOCATION": {"reason_code": "WINDOW_NOT_COMPLETE", "status": "NOT_EVALUATED", "value": None},
                "MOTION": {"reason_code": "WINDOW_NOT_COMPLETE", "status": "NOT_EVALUATED", "value": None},
                "ORGANISATION": {"reason_code": "WINDOW_NOT_COMPLETE", "status": "NOT_EVALUATED", "value": None},
                "QUALITY": {"reason_code": "WINDOW_NOT_COMPLETE", "status": "EVALUATED", "value": "CENSORED"},
            },
            "c1_manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1",
            "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
            "clock": "15M",
            "container_ids": [],
            "continuity": "RESET",
            "evaluation_scope_id": "GBPUSD-15M-WITH-2H-PARENT-v0.1",
            "first_valid_time": "2021-01-03T22:15:00Z",
            "level_ids": [],
            "opt_a_manifest_id": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
            "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "parameter_pack_id": "C2.PARAMS.GBPUSD.DISCOVERY.v0.1",
            "parent_c1_record_id": "c1:a5698c68387c5edc17c70194b90cdddf5e1c9f0e2642b9326bbcfd054992a315",
            "parent_opt_a_bar_id": "opt-a:6e11673fcd782e579536a62fd39bf5d858e70d13e4fdecafd6ec84f30234a41b",
            "persistence": {"INTERACTION": 1, "LOCATION": 1, "MOTION": 1, "ORGANISATION": 1, "QUALITY": 1},
            "relation_set_id": "c2-relset:c9ae794428e1a3a221aa2254c3ddfa765321ecb886f0042f61a52ade53c71c73",
            "role": "DISCOVERY",
            "side": "ASK",
        }
        self.row["c2_state_id"] = MODULE.stable_id(
            "c2-state",
            MODULE.state_identity(self.row, self.row["c1_release_id"]),
        )

    def test_known_v1_identity_matches_frozen_replay(self) -> None:
        self.assertEqual(
            self.row["c2_state_id"],
            "c2-state:2b8240ebd0933988e2cff9605c5a461daf22ceef2fe7a7f5a150e363dae26dbf",
        )

    def test_v2_rebinding_changes_identity_but_not_semantics(self) -> None:
        rebound = dict(self.row)
        rebound["c1_release_id"] = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2"
        rebound["c1_manifest_id"] = "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1"
        rebound["c2_state_id"] = MODULE.stable_id(
            "c2-state",
            MODULE.state_identity(rebound, rebound["c1_release_id"]),
        )
        self.assertNotEqual(rebound["c2_state_id"], self.row["c2_state_id"])
        self.assertEqual(MODULE.semantic_state(rebound), MODULE.semantic_state(self.row))

    def test_transition_identity_rebinds_endpoints_only(self) -> None:
        old = {
            "c2_transition_id": "",
            "changed_axes": ["INTERACTION"],
            "clock": "15M",
            "evaluation_scope_id": "GBPUSD-15M-WITH-2H-PARENT-v0.1",
            "first_valid_time": "2021-01-04T01:45:00Z",
            "from_state_id": "c2-state:old-from",
            "role": "DISCOVERY",
            "side": "ASK",
            "status": "OBSERVED",
            "to_state_id": "c2-state:old-to",
        }
        old["c2_transition_id"] = MODULE.stable_id(
            "c2-transition",
            {
                "from": old["from_state_id"],
                "to": old["to_state_id"],
                "changed_axes": old["changed_axes"],
                "first_valid_time": old["first_valid_time"],
            },
        )
        new = dict(old)
        new["from_state_id"] = "c2-state:new-from"
        new["to_state_id"] = "c2-state:new-to"
        new["c2_transition_id"] = MODULE.stable_id(
            "c2-transition",
            {
                "from": new["from_state_id"],
                "to": new["to_state_id"],
                "changed_axes": new["changed_axes"],
                "first_valid_time": new["first_valid_time"],
            },
        )
        self.assertNotEqual(new["c2_transition_id"], old["c2_transition_id"])
        self.assertEqual(MODULE.semantic_transition(new), MODULE.semantic_transition(old))


if __name__ == "__main__":
    unittest.main()
