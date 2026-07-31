from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.v0_4 import (
    DeclaredSampleRequired,
    RO4IndexError,
    assess_window_cardinality,
    build_full_index,
    deterministic_sample_ids,
    validate_index,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_4/RO4_G1_SYNTHETIC_SOURCE_FIXTURE_v0_1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def materialize(root: Path) -> tuple[Path, Path]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    releases = []
    partitions = []
    for role in ("DISCOVERY", "DEVELOPMENT"):
        role_key = role.lower()
        records = fixture["roles"][role]
        state_rel = f"states/{role_key}/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        transition_rel = f"transitions/{role_key}/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        state_path = root / state_rel
        transition_path = root / transition_rel
        write_jsonl(state_path, records["states"])
        write_jsonl(transition_path, records["transitions"])
        if role == "DISCOVERY":
            release = {
                "role": role,
                "authority": "ACTIVE_DISCOVERY",
                "release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
                "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
                "manifest_sha256": "c" * 64,
                "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2",
                "c1_manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1",
                "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
                "opt_a_manifest_id": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
            }
        else:
            release = {
                "role": role,
                "authority": "REMOTE_VERIFIED_REFERENCE_ONLY",
                "release_id": "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2",
                "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2.r1",
                "manifest_sha256": "4" * 64,
                "c1_release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2",
                "c1_manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1",
                "opt_a_release_id": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
                "opt_a_manifest_id": "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
            }
        release.update(state_record_count=len(records["states"]), transition_record_count=len(records["transitions"]))
        releases.append(release)
        partitions.append(
            {
                "partition_id": f"{role}.15M.BID.GBPUSD-15M-LOCAL-v0_1",
                "role": role,
                "clock": "15M",
                "side": "BID",
                "evaluation_scope_id": "GBPUSD-15M-LOCAL-v0.1",
                "state_path": state_rel,
                "state_sha256": sha(state_path),
                "state_size_bytes": state_path.stat().st_size,
                "state_record_count": len(records["states"]),
                "transition_path": transition_rel,
                "transition_sha256": sha(transition_path),
                "transition_size_bytes": transition_path.stat().st_size,
                "transition_record_count": len(records["transitions"]),
            }
        )
    inventory = {
        "schema": "ovc-ro4-g1-source-inventory/v1",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "releases": releases,
        "partitions": partitions,
    }
    inventory_path = root / "inventory.json"
    inventory_path.write_text(json.dumps(inventory, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return root, inventory_path


class RO4G1IndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source, self.inventory = materialize(self.root / "source")
        self.output = self.root / "index"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_full_build_reconciles_and_validates(self) -> None:
        result = build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)
        self.assertEqual(result.manifest["state_record_count"], 6)
        self.assertEqual(result.manifest["transition_record_count"], 4)
        self.assertEqual(validate_index(self.output, self.inventory)["status"], "PASS")

    def test_deterministic_rerun_is_byte_identical(self) -> None:
        first = build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)
        second_output = self.root / "index2"
        second = build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=second_output)
        self.assertEqual(first.manifest["logical_hash"], second.manifest["logical_hash"])
        first_hashes = [item["index_file_sha256"] for item in first.manifest["partitions"]]
        second_hashes = [item["index_file_sha256"] for item in second.manifest["partitions"]]
        self.assertEqual(first_hashes, second_hashes)

    def test_incremental_rebuild_preserves_unchanged_hashes(self) -> None:
        build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)
        result = build_full_index(
            source_root=self.source,
            inventory_path=self.inventory,
            output_dir=self.output,
            selected_partition="DEVELOPMENT.15M.BID.GBPUSD-15M-LOCAL-v0_1",
        )
        self.assertTrue(result.benchmark["unchanged_hashes_preserved"])

    def test_validation_is_denied_before_path_resolution(self) -> None:
        inventory = json.loads(self.inventory.read_text())
        inventory["releases"].append({"role": "VALIDATION"})
        self.inventory.write_text(json.dumps(inventory))
        shutil.rmtree(self.source / "states")
        with self.assertRaisesRegex(RO4IndexError, "ROLE_DENIED_BEFORE_PATH_RESOLUTION:VALIDATION"):
            build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)

    def test_source_hash_mismatch_blocks_without_fallback(self) -> None:
        path = self.source / "states/discovery/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        path.write_text(path.read_text() + "{}\n")
        with self.assertRaisesRegex(RO4IndexError, "SOURCE_SIZE_MISMATCH"):
            build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)

    def test_missing_transition_endpoint_blocks(self) -> None:
        path = self.source / "transitions/discovery/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["from_state_id"] = "c2-state:" + "f" * 64
        write_jsonl(path, rows)
        inventory = json.loads(self.inventory.read_text())
        part = next(item for item in inventory["partitions"] if item["role"] == "DISCOVERY")
        part["transition_sha256"] = sha(path)
        part["transition_size_bytes"] = path.stat().st_size
        self.inventory.write_text(json.dumps(inventory))
        with self.assertRaisesRegex(RO4IndexError, "TRANSITION_ENDPOINT_MISSING"):
            build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)

    def test_duplicate_state_identity_blocks(self) -> None:
        path = self.source / "states/discovery/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[1]["c2_state_id"] = rows[0]["c2_state_id"]
        write_jsonl(path, rows)
        inventory = json.loads(self.inventory.read_text())
        part = next(item for item in inventory["partitions"] if item["role"] == "DISCOVERY")
        part["state_sha256"] = sha(path)
        part["state_size_bytes"] = path.stat().st_size
        self.inventory.write_text(json.dumps(inventory))
        with self.assertRaisesRegex(RO4IndexError, "DUPLICATE_OR_FOREIGN_KEY_FAILURE"):
            build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)

    def test_overall_state_field_is_denied(self) -> None:
        path = self.source / "states/discovery/15M/BID/GBPUSD-15M-LOCAL-v0_1.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["overall_state"] = "UP"
        write_jsonl(path, rows)
        inventory = json.loads(self.inventory.read_text())
        part = next(item for item in inventory["partitions"] if item["role"] == "DISCOVERY")
        part["state_sha256"] = sha(path)
        part["state_size_bytes"] = path.stat().st_size
        self.inventory.write_text(json.dumps(inventory))
        with self.assertRaisesRegex(RO4IndexError, "FORBIDDEN_FIELD"):
            build_full_index(source_root=self.source, inventory_path=self.inventory, output_dir=self.output)

    def test_window_cap_requires_explicit_declared_sample(self) -> None:
        with self.assertRaises(DeclaredSampleRequired):
            assess_window_cardinality(100_100, [2, 3], cap=100_000)
        result = assess_window_cardinality(
            100_100,
            [2, 3],
            cap=100_000,
            declared_sample_manifest={
                "mode": "DECLARED_SAMPLE_MODE",
                "authority": "SAMPLED_NON_CANONICAL_EXPLORATORY",
            },
        )
        self.assertEqual(result["mode"], "DECLARED_SAMPLE_MODE")

    def test_declared_sample_is_deterministic(self) -> None:
        values = [f"sequence:{i}" for i in range(100)]
        first = deterministic_sample_ids(values, sample_size=10, sampling_policy_id="RO4.SAMPLE.v1", sampling_version="v1")
        second = deterministic_sample_ids(reversed(values), sample_size=10, sampling_policy_id="RO4.SAMPLE.v1", sampling_version="v1")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
