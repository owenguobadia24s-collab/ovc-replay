from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import unittest

from ovc.opt_b.srfd.scheduler import (
    CapacityBudget,
    CapacityScheduleError,
    ResourceContract,
    build_capacity_plan,
    classify_capacity_status,
    controlled_capacity_failure,
)


T0 = CapacityBudget.from_values(
    "T0",
    max_wall_seconds="14400",
    max_rss_bytes=16 * 1024**3,
    max_external_bytes=10 * 1024**3,
)
T1 = CapacityBudget.from_values(
    "T1",
    max_wall_seconds="86400",
    max_rss_bytes=32 * 1024**3,
    max_external_bytes=100 * 1024**3,
)
METHODS = (
    "AVERAGE_LINKAGE",
    "BOUNDED_PAM",
    "COMPLETE_LINKAGE",
    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
)
REQUIRED = tuple((method, "CFG-A") for method in METHODS)


def _contracts() -> list[dict[str, object]]:
    values: list[dict[str, object]] = [
        {
            "node_id": "00.representation",
            "node_type": "REPRESENTATION",
            "dependency_ids": [],
            "wall_seconds": "20",
            "peak_rss_bytes": 512 * 1024**2,
            "external_bytes": 128 * 1024**2,
            "measurement_class": "MEASURED",
            "reusable": True,
        },
        {
            "node_id": "10.distance.shared",
            "node_type": "DISTANCE",
            "dependency_ids": ["00.representation"],
            "wall_seconds": "100",
            "peak_rss_bytes": 1024 * 1024**2,
            "external_bytes": 512 * 1024**2,
            "measurement_class": "MEASURED",
            "reusable": True,
        },
    ]
    for index, method in enumerate(METHODS):
        values.append(
            {
                "node_id": f"20.family.{index}.{method}",
                "node_type": "FAMILY_METHOD",
                "method_id": method,
                "configuration_id": "CFG-A",
                "dependency_ids": ["10.distance.shared"],
                "wall_seconds": str(200 + index),
                "peak_rss_bytes": 2 * 1024**3,
                "external_bytes": 256 * 1024**2,
                "measurement_class": "MEASURED",
                "required": True,
            }
        )
    return values


class SRFDIG8RWP4SchedulerTests(unittest.TestCase):
    def test_plan_is_deterministic_complete_and_reuses_shared_dependency(self) -> None:
        plan_a = build_capacity_plan(
            _contracts(), required_method_configurations=REQUIRED, t0=T0, t1=T1
        )
        plan_b = build_capacity_plan(
            list(reversed(_contracts())),
            required_method_configurations=tuple(reversed(REQUIRED)),
            t0=T0,
            t1=T1,
        )
        self.assertEqual(plan_a, plan_b)
        self.assertEqual("00.representation", plan_a["execution_order"][0])
        self.assertEqual("10.distance.shared", plan_a["execution_order"][1])
        self.assertEqual(6, len(plan_a["execution_order"]))
        self.assertEqual(4, len(plan_a["required_method_configurations"]))
        self.assertEqual("PROHIBITED", plan_a["partial_benchmark_escape_hatch"])
        self.assertFalse(plan_a["june_market_records_read"])
        self.assertFalse(plan_a["validation_consumed"])
        self.assertEqual("NONE", plan_a["scientific_effect"])

    def test_missing_or_extra_required_method_configuration_fails_closed(self) -> None:
        contracts = _contracts()
        contracts.pop()
        with self.assertRaisesRegex(CapacityScheduleError, "CAP_METHOD_CONFIG_INCOMPLETE"):
            build_capacity_plan(
                contracts, required_method_configurations=REQUIRED, t0=T0, t1=T1
            )
        contracts = _contracts()
        contracts.append(
            {
                "node_id": "20.family.extra",
                "node_type": "FAMILY_METHOD",
                "method_id": "EXTRA_METHOD",
                "configuration_id": "CFG-A",
                "dependency_ids": ["10.distance.shared"],
                "wall_seconds": "1",
                "peak_rss_bytes": 1,
                "external_bytes": 1,
                "measurement_class": "MEASURED",
                "required": True,
            }
        )
        with self.assertRaisesRegex(CapacityScheduleError, "CAP_METHOD_CONFIG_INCOMPLETE"):
            build_capacity_plan(
                contracts, required_method_configurations=REQUIRED, t0=T0, t1=T1
            )

    def test_missing_dependency_and_cycle_fail_closed(self) -> None:
        contracts = _contracts()
        contracts[1]["dependency_ids"] = ["missing"]
        with self.assertRaisesRegex(CapacityScheduleError, "CAP_DEPENDENCY_MISSING"):
            build_capacity_plan(
                contracts, required_method_configurations=REQUIRED, t0=T0, t1=T1
            )
        contracts = _contracts()
        contracts[0]["dependency_ids"] = ["10.distance.shared"]
        with self.assertRaisesRegex(CapacityScheduleError, "CAP_DEPENDENCY_CYCLE"):
            build_capacity_plan(
                contracts, required_method_configurations=REQUIRED, t0=T0, t1=T1
            )

    def test_status_vocabulary_distinguishes_t0_t1_unresolved_and_exceeded(self) -> None:
        base = ResourceContract.from_mapping(
            {
                "node_id": "family",
                "node_type": "FAMILY_METHOD",
                "method_id": "AVERAGE_LINKAGE",
                "configuration_id": "CFG-A",
                "dependency_ids": [],
                "wall_seconds": "100",
                "peak_rss_bytes": 100,
                "external_bytes": 100,
                "measurement_class": "MEASURED",
            }
        )
        self.assertEqual("SUPPORTED_T0", classify_capacity_status(base, t0=T0, t1=T1).status)
        t1_only = ResourceContract(
            **{**base.__dict__, "wall_seconds": Decimal("20000")}
        )
        self.assertEqual(
            "METHOD_CAPACITY_UNSUPPORTED_AT_T0",
            classify_capacity_status(t1_only, t0=T0, t1=T1).status,
        )
        unresolved = ResourceContract(
            **{**base.__dict__, "wall_seconds": None}
        )
        self.assertEqual(
            "CAPACITY_UNRESOLVED",
            classify_capacity_status(unresolved, t0=T0, t1=T1).status,
        )
        self.assertEqual(
            "CAPACITY_EXCEEDED_AT_MEASUREMENT",
            classify_capacity_status(base, t0=T0, t1=T1, measured_exceeded=True).status,
        )
        too_large = ResourceContract(
            **{**base.__dict__, "wall_seconds": Decimal("90000")}
        )
        self.assertEqual(
            "REQUIRES_SEPARATE_CAPACITY_TIER",
            classify_capacity_status(too_large, t0=T0, t1=T1).status,
        )

    def test_unresolved_dependency_blocks_downstream_without_dropping_it(self) -> None:
        contracts = _contracts()
        contracts[1]["wall_seconds"] = None
        plan = build_capacity_plan(
            contracts, required_method_configurations=REQUIRED, t0=T0, t1=T1
        )
        self.assertEqual(4, len(plan["blocked_nodes"]))
        self.assertTrue(
            all("10.distance.shared" in reason for reason in plan["blocked_nodes"].values())
        )
        self.assertEqual(6, len(plan["execution_order"]))

    def test_controlled_failure_preserves_method_and_has_no_authority_effect(self) -> None:
        receipt = controlled_capacity_failure(
            node_id="20.family.0.AVERAGE_LINKAGE",
            status="METHOD_CAPACITY_UNSUPPORTED_AT_T0",
            measured={"wall_seconds": "16000"},
        )
        self.assertEqual(
            "STOP_NODE_PRESERVE_EVIDENCE_DO_NOT_DROP_METHOD", receipt["action"]
        )
        self.assertEqual("NONE", receipt["scientific_effect"])
        self.assertEqual("NONE", receipt["authority_effect"])
        self.assertEqual("PROHIBITED", receipt["partial_benchmark_escape_hatch"])
        with self.assertRaisesRegex(CapacityScheduleError, "CAP_INVALID_FAILURE"):
            controlled_capacity_failure(node_id="x", status="SUPPORTED_T0")

    def test_registry_and_contract_preserve_authority_firewalls(self) -> None:
        root = Path(__file__).resolve().parents[3]
        registry = (root / "registries/research/srfd/method_capacity_status_v0_2.yaml").read_text()
        contract = (root / "contracts/research/srfd/method_capacity_contract_v0_2.md").read_text()
        for method in METHODS:
            self.assertIn(method, registry)
        self.assertIn("partial_benchmark_escape_hatch: PROHIBITED", registry)
        self.assertIn("canonical_family_method: NONE", registry)
        self.assertIn("wp9: DENIED", registry)
        self.assertIn("june: DENIED", registry)
        self.assertIn("validation_2025: LOCKED_UNCONSUMED", registry)
        self.assertIn("scientific_effect: NONE", registry)
        self.assertIn("scientific_effect=NONE", contract)
        self.assertIn("PR #371", contract)


if __name__ == "__main__":
    unittest.main()
