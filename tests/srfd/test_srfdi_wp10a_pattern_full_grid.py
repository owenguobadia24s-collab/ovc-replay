from __future__ import annotations

from decimal import Decimal
from itertools import combinations
import unittest

from ovc.opt_b.srfd.families import (
    DistanceMatrix,
    FamilyMethodSpec,
    bounded_pam,
    hierarchical,
    medoid_star,
)
from ovc.opt_b.srfd.family_grid_capacity import frozen_hierarchical_configuration_id
from ovc.opt_b.srfd.family_grid_reuse import (
    frozen_medoid_configuration_id,
    frozen_pam_configuration_id,
)
from ovc.opt_b.srfd.pattern_family_capacity import (
    PatternDistanceSurface,
    materialize_pattern_full_grid,
)


RADII = ("0.04", "0.08", "0.16")
SUPPORTS = (2, 4, 8)
PAM_K = (2, 4, 8)
PAM_RADII = ("0.10", "0.20", "0.40")


def record(record_id: str, vector: tuple[str, ...], *, fields: tuple[str, ...]) -> dict[str, object]:
    return {
        "representation_id": record_id,
        "structural_raw": {field: value for field, value in zip(fields, vector)},
        "structural_derived": {},
        "structural_normalized": {},
        "comparison_only": {},
        "missingness": [],
        "comparability_domain_id": "D",
        "ordering_semantics": "STATIC_VECTOR",
    }


def getter(item: dict[str, object], field: str) -> object:
    return item["structural_raw"][field]  # type: ignore[index]


def dense_matrix(records: list[dict[str, object]], fields: tuple[str, ...]) -> DistanceMatrix:
    ids = sorted(str(item["representation_id"]) for item in records)
    by_id = {str(item["representation_id"]): item for item in records}
    quantum = Decimal("0.000000000001")
    values: dict[str, str] = {}
    for left, right in combinations(ids, 2):
        left_values = tuple(getter(by_id[left], field) for field in fields)
        right_values = tuple(getter(by_id[right], field) for field in fields)
        mismatches = sum(a != b for a, b in zip(left_values, right_values))
        distance = (Decimal(mismatches) / Decimal(len(fields))).quantize(quantum)
        values[f"{left}|{right}"] = format(distance, "f")
    return DistanceMatrix.from_pairs(ids, values)


def reference_grid(matrix: DistanceMatrix, *, domain_id: str) -> dict[str, dict[str, object]]:
    catalogs: dict[str, dict[str, object]] = {}
    for linkage, method_id in (("complete", "COMPLETE_LINKAGE"), ("average", "AVERAGE_LINKAGE")):
        for radius in RADII:
            for support in SUPPORTS:
                config = frozen_hierarchical_configuration_id(
                    domain_id=domain_id,
                    linkage=linkage,
                    radius=radius,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    method_id,
                    config,
                    radius=radius,
                    minimum_support=support,
                    linkage=linkage,
                )
                catalogs[config] = hierarchical(matrix, spec)
    for radius in RADII:
        for support in SUPPORTS:
            config = frozen_medoid_configuration_id(
                domain_id=domain_id,
                radius=radius,
                minimum_support=support,
            )
            spec = FamilyMethodSpec(
                "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                config,
                radius=radius,
                minimum_support=support,
            )
            catalogs[config] = medoid_star(matrix, spec)
    for k in PAM_K:
        for assignment_radius in PAM_RADII:
            for support in SUPPORTS:
                config = frozen_pam_configuration_id(
                    domain_id=domain_id,
                    k=k,
                    max_assignment_distance=assignment_radius,
                    max_iterations=8,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    "BOUNDED_PAM",
                    config,
                    k=k,
                    minimum_support=support,
                    max_assignment_distance=assignment_radius,
                    max_iterations=8,
                )
                catalogs[config] = bounded_pam(matrix, spec)
    return catalogs


class SRFDIWP10APatternFullGridTests(unittest.TestCase):
    def assert_full_grid_equivalent(self, records: list[dict[str, object]], fields: tuple[str, ...], *, domain_id: str) -> None:
        surface = PatternDistanceSurface.from_records(records, fields=fields, value_getter=getter)
        actual = materialize_pattern_full_grid(surface, domain_id=domain_id)
        expected = reference_grid(dense_matrix(records, fields), domain_id=domain_id)
        self.assertEqual(54, actual["configuration_count"])
        self.assertEqual(set(expected), set(actual["catalogs"]))
        for configuration_id in sorted(expected):
            self.assertEqual(
                expected[configuration_id],
                actual["catalogs"][configuration_id],
                configuration_id,
            )

    def test_duplicate_patterns_unbalanced_multiplicity_and_lexicographic_ties(self) -> None:
        fields = tuple(f"F{i:02d}" for i in range(25))
        base = tuple("A" for _ in fields)

        def mutate(*indices: int) -> tuple[str, ...]:
            values = list(base)
            for index in indices:
                values[index] = "B"
            return tuple(values)

        vectors = [
            base,
            base,
            base,
            base,
            mutate(0),                 # exact 0.04 boundary
            mutate(0),
            mutate(1, 2),              # exact 0.08 boundary
            mutate(1, 2),
            mutate(3, 4, 5, 6),        # exact 0.16 boundary
            mutate(3, 4, 5, 6),
            mutate(0, 1, 2, 3, 4),
            mutate(5, 6, 7, 8, 9, 10),
        ]
        ids = ["A00", "A01", "A02", "A03", "B00", "B01", "C00", "C01", "D00", "D01", "E00", "F00"]
        records = [record(record_id, vector, fields=fields) for record_id, vector in zip(ids, vectors)]
        self.assert_full_grid_equivalent(records, fields, domain_id="DUPLICATE-BOUNDARY")

    def test_realistic_r1_ten_categorical_fields_with_many_duplicate_patterns(self) -> None:
        fields = tuple(
            value
            for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
            for value in (f"{axis}.status", f"{axis}.value")
        )
        patterns = [
            tuple("EVALUATED" if index % 2 == 0 else "A" for index in range(len(fields))),
            tuple("EVALUATED" if index % 2 == 0 else "B" for index in range(len(fields))),
            tuple("EVALUATED" if index % 2 == 0 else ("A" if index < 5 else "B") for index in range(len(fields))),
            tuple("EVALUATED" if index % 2 == 0 else ("B" if index < 5 else "A") for index in range(len(fields))),
        ]
        records: list[dict[str, object]] = []
        for index in range(16):
            records.append(record(f"R{index:02d}", patterns[index % len(patterns)], fields=fields))
        self.assert_full_grid_equivalent(records, fields, domain_id="R1-LIKE")

    def test_null_control_fast_path_matches_reference_for_all_54_configs(self) -> None:
        fields = ("null_control_token",)
        records = [record(f"N{index:02d}", (f"UNIQUE::{index:02d}",), fields=fields) for index in range(12)]
        surface = PatternDistanceSurface.from_records(records, fields=fields, value_getter=getter)
        actual = materialize_pattern_full_grid(
            surface,
            domain_id="NULL-CONTROL",
            null_control_all_off_diagonal_one=True,
        )
        expected = reference_grid(dense_matrix(records, fields), domain_id="NULL-CONTROL")
        self.assertEqual(12, surface.unique_pattern_count)
        self.assertEqual(54, actual["configuration_count"])
        for configuration_id in sorted(expected):
            self.assertEqual(expected[configuration_id], actual["catalogs"][configuration_id], configuration_id)
            self.assertEqual("NO_STABLE_FAMILY", actual["catalogs"][configuration_id]["evidence_status"])

    def test_pattern_distance_preserves_exact_twelve_decimal_gower_quantization(self) -> None:
        fields = tuple(f"Q{i:02d}" for i in range(15))
        left = tuple("A" for _ in fields)
        right = tuple("B" if index == 0 else "A" for index in range(len(fields)))
        records = [record("L", left, fields=fields), record("R", right, fields=fields)]
        surface = PatternDistanceSurface.from_records(records, fields=fields, value_getter=getter)
        self.assertEqual(Decimal("0.066666666667"), surface.distance("L", "R"))


if __name__ == "__main__":
    unittest.main()
