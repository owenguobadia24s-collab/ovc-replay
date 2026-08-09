from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.opt_b.srfd.pattern_family_capacity import materialize_pattern_full_grid
from ovc.opt_b.srfd.sensitivity import build_invariant_cores, method_disagreement
from ovc.opt_b.srfd.wp10_execution_resilience import RunBinding
from ovc.opt_b.srfd.wp10_v07_contract import (
    FROZEN_CAPACITY_GRID_SHA256,
    FROZEN_ELIGIBLE_IDS_SHA256,
    FROZEN_POPULATION_ID,
    FROZEN_PREREGISTRATION_SHA256,
    FROZEN_REPRESENTATION_PACK_SHA256,
    FROZEN_SCIENTIFIC_MANIFEST_SHA256,
    FROZEN_SEGMENTATION_PACK_SHA256,
    FROZEN_SOURCE_BINDING_SHA256,
    FROZEN_STABILITY_PACK_SHA256,
    WP10RunnerError,
    verify_frozen_run_binding,
)
from ovc.opt_b.srfd.wp10_v07_analysis import (
    build_invariant_core_support_exact,
    method_disagreement_exact,
)
from ovc.opt_b.srfd.wp10_v07_family import (
    frozen_configuration_plan,
    gower_pattern_surface,
    materialize_prepared_configuration,
    prepare_domain,
)
from ovc.opt_b.srfd.wp10_v07_runner import planned_work_units, start_wp10


def exact_binding(**changes: str) -> RunBinding:
    values = {
        "programme_id": "OVC-SRFD-BENCHMARK-v0.1",
        "packet_id": "SRFDI-WP10-v0.7",
        "population_id": FROZEN_POPULATION_ID,
        "eligible_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256,
        "scientific_manifest_sha256": FROZEN_SCIENTIFIC_MANIFEST_SHA256,
        "preregistration_sha256": FROZEN_PREREGISTRATION_SHA256,
        "representation_pack_sha256": FROZEN_REPRESENTATION_PACK_SHA256,
        "segmentation_pack_sha256": FROZEN_SEGMENTATION_PACK_SHA256,
        "stability_pack_sha256": FROZEN_STABILITY_PACK_SHA256,
        "source_binding_sha256": FROZEN_SOURCE_BINDING_SHA256,
        "capacity_grid_sha256": FROZEN_CAPACITY_GRID_SHA256,
        "implementation_commit": "a" * 64,
    }
    values.update(changes)
    return RunBinding(**values)


def catalog(catalog_id, method, cfg, families, residual=()):
    return {
        "family_catalog_id": catalog_id,
        "method_id": method,
        "configuration_id": cfg,
        "families": [
            {"family_id": family_id, "member_ids": list(members)}
            for family_id, members in families
        ],
        "residual_ids": list(residual),
        "noise_ids": [],
        "evidence_status": "FAMILY_EVIDENCE_PRESENT" if families else "NO_STABLE_FAMILY",
    }


class SRFDIWP10V07RunnerTests(unittest.TestCase):
    def test_frozen_configuration_plan_is_exact_54_per_domain(self) -> None:
        plan = frozen_configuration_plan("SRFD.COMP.TEST")
        self.assertEqual(54, len(plan))
        counts = {}
        for item in plan:
            counts[item.family_method_id] = counts.get(item.family_method_id, 0) + 1
        self.assertEqual(
            {
                "COMPLETE_LINKAGE": 9,
                "AVERAGE_LINKAGE": 9,
                "GREEDY_LEXICOGRAPHIC_MEDOID_STAR": 9,
                "BOUNDED_PAM": 27,
            },
            counts,
        )

    def test_work_plan_checkpoints_each_family_configuration(self) -> None:
        domains = [f"D{index:02d}" for index in range(36)]
        units = planned_work_units(domains)
        self.assertEqual(2020, len(units))
        family_units = [unit for unit in units if "/configuration/" in unit]
        self.assertEqual(1944, len(family_units))
        self.assertEqual(len(family_units), len(set(family_units)))

    def test_per_configuration_materialization_matches_full_grid(self) -> None:
        records = []
        for index in range(8):
            records.append(
                {
                    "representation_id": f"R{index:02d}",
                    "implementation_class_id": "SRFDI-R1",
                    "representation_variant_id": None,
                    "first_valid_time": f"2026-06-{index + 1:02d}T00:00:00Z",
                    "structural_raw": {
                        "A.value": "UP" if index % 2 else "DOWN",
                        "B.value": str(index % 3),
                    },
                    "structural_derived": {},
                    "structural_normalized": {},
                    "comparison_only": {},
                }
            )
        domain_id = "SRFD.COMP.TEST"
        surface = gower_pattern_surface(records)
        full = materialize_pattern_full_grid(surface, domain_id=domain_id)
        preparation = prepare_domain(records, domain_id)
        for descriptor in frozen_configuration_plan(domain_id):
            actual = materialize_prepared_configuration(
                records, preparation, descriptor
            )["catalog"]
            self.assertEqual(full["catalogs"][descriptor.configuration_id], actual)

    def test_capacity_safe_invariant_and_disagreement_match_reference(self) -> None:
        a = catalog("A", "M1", "1", [("A1", ("X", "Y", "Z"))])
        b = catalog("B", "M2", "2", [("B1", ("X", "Y")), ("B2", ("Z", "Q"))])
        c = catalog("C", "M3", "3", [("C1", ("X", "Y", "R"))])
        self.assertEqual(
            build_invariant_cores([c, a, b], minimum_catalog_support=2),
            build_invariant_core_support_exact([c, a, b]),
        )
        d = catalog("D", "M4", "4", [("D1", ("X", "Q"))], residual=("Y", "Z", "R"))
        self.assertEqual(
            method_disagreement([d, a]),
            method_disagreement_exact([d, a]),
        )

    def test_binding_drift_is_rejected_before_execution(self) -> None:
        verify_frozen_run_binding(exact_binding())
        with self.assertRaises(WP10RunnerError) as ctx:
            verify_frozen_run_binding(exact_binding(population_id="SRFD.POP.DRIFT"))
        self.assertEqual("RUN_BINDING_SCIENCE_DRIFT", ctx.exception.reason_code)

    def test_preflight_failure_occurs_before_token_consumption(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            with patch(
                "ovc.opt_b.srfd.wp10_v07_runner.preflight_wp10",
                side_effect=WP10RunnerError("DURABLE_STORE_UNAVAILABLE", "synthetic"),
            ):
                with self.assertRaises(WP10RunnerError):
                    start_wp10(
                        token={
                            "token_id": "SRFD.JUNE.AUTH.NOT.CONSUMED",
                            "state": "AUTHORIZED_UNCONSUMED",
                            "single_use": True,
                            "run_binding_sha256": exact_binding().logical_hash,
                        },
                        binding=exact_binding(),
                        source_paths={},
                        pack_registry={},
                        segmentation_registry={},
                        stability_registry={},
                        durable_root=root,
                    )
            self.assertEqual([], list(root.rglob("*.json")))


if __name__ == "__main__":
    unittest.main()
