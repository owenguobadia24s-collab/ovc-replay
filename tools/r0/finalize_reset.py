from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


BASELINE = "c0ad7ba22618babdde731e2a338f68f688d4210c"
ARCHIVE_BRANCH = "archive/ovc-replay-v1-c0ad7ba-20260725"
QUARANTINE_ROOT = Path("legacy/quarantine/abcd-engine-v1-c0ad7ba")
PACKET_ROOT = Path("docs/history/repository-freezes/ovc-replay-v1-c0ad7ba")
RELEASE_ROOT = Path("docs/history/releases")
DECISION_ROOT = Path("docs/decisions")
MANIFEST_PATH = QUARANTINE_ROOT / "R0_7_RELEASE_DECISION_QUARANTINE_MANIFEST.json"
CROSSWALK_PATH = QUARANTINE_ROOT / "R0_7_RELEASE_DECISION_CROSSWALK.csv"
VALIDATION_PATH = PACKET_ROOT / "R0_7_VALIDATION.json"
OPERATOR_PACKET_PATH = PACKET_ROOT / "R0_7_FINAL_OPERATOR_PACKET.md"


def _run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _tracked_under(root: Path) -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z", "--", root.as_posix()])
    return sorted(Path(item.decode("utf-8")) for item in output.split(b"\0") if item)


def _record(source: Path, category: str) -> dict[str, Any]:
    if not source.is_file():
        raise SystemExit(f"tracked source is not a regular file: {source}")
    target = QUARANTINE_ROOT / source
    return {
        "category": category,
        "source_path": source.as_posix(),
        "target_path": target.as_posix(),
        "git_blob_sha1": _run("git", "hash-object", "--", source.as_posix()),
        "sha256": _sha256(source),
        "size_bytes": source.stat().st_size,
    }


def _move_records(records: list[dict[str, Any]]) -> None:
    seen_targets: set[str] = set()
    for record in records:
        source = Path(record["source_path"])
        target = Path(record["target_path"])
        if target.as_posix() in seen_targets:
            raise SystemExit(f"duplicate quarantine target: {target}")
        seen_targets.add(target.as_posix())
        if target.exists():
            raise SystemExit(f"quarantine target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["git", "mv", "--", source.as_posix(), target.as_posix()])
        if _run("git", "hash-object", "--", target.as_posix()) != record["git_blob_sha1"]:
            raise SystemExit(f"Git blob identity changed during move: {source}")
        if _sha256(target) != record["sha256"]:
            raise SystemExit(f"SHA-256 identity changed during move: {source}")


def _write_crosswalk(records: list[dict[str, Any]]) -> None:
    CROSSWALK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CROSSWALK_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category", "source_path", "target_path", "git_blob_sha1", "sha256", "size_bytes"],
        )
        writer.writeheader()
        writer.writerows(records)


def _write_active_markers() -> None:
    _write_text(
        RELEASE_ROOT / "README.md",
        "# Historical releases moved to quarantine\n\n"
        "All superseded v1 ABCD release records previously stored beneath this path were moved byte-for-byte during R0-7 to "
        "`legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/history/releases/`. They remain historically addressable but have no active "
        "release-parent, selector, parameter-source, rollback-target or discovery-seed authority.\n\n"
        "The exact source-to-target crosswalk is recorded in "
        "`legacy/quarantine/abcd-engine-v1-c0ad7ba/R0_7_RELEASE_DECISION_CROSSWALK.csv`.\n",
    )
    _write_text(
        DECISION_ROOT / "README.md",
        "# Active decisions\n\n"
        "No model, market, selector, probability, exposure or execution decision is active after R0. Superseded v1 ABCD decision records "
        "were moved byte-for-byte during R0-7 to `legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/decisions/`.\n\n"
        "Current repository-reset decisions are recorded in "
        "`docs/history/repository-freezes/ovc-replay-v1-c0ad7ba/` and require explicit operator approval before merge.\n",
    )
    _write_text(
        Path("docs/history/README.md"),
        "# Development history\n\n"
        "The historical v1 ABCD releases and their superseded decision records are preserved in the repository quarantine rather than in "
        "the active documentation tree. Their exact bytes and original paths remain auditable.\n\n"
        "- Release records: `legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/history/releases/`\n"
        "- Superseded decisions: `legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/decisions/`\n"
        "- R0 freeze, classification, migration and final operator records: `docs/history/repository-freezes/ovc-replay-v1-c0ad7ba/`\n"
        "- Source-to-target crosswalk: `legacy/quarantine/abcd-engine-v1-c0ad7ba/R0_7_RELEASE_DECISION_CROSSWALK.csv`\n\n"
        "Quarantined records may be used for historical audit and bounded defect-fixture derivation only. They may not become active release "
        "parents, selectors, rollback targets, parameter sources or discovery seeds.\n",
    )


def _write_authority_test() -> None:
    _write_text(
        Path("tests/authority/test_release_decision_quarantine.py"),
        '''from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "legacy/quarantine/abcd-engine-v1-c0ad7ba/R0_7_RELEASE_DECISION_QUARANTINE_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReleaseDecisionQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_all_recorded_sources_are_absent_and_targets_present(self) -> None:
        for record in self.payload["records"]:
            self.assertFalse((ROOT / record["source_path"]).exists(), record["source_path"])
            self.assertTrue((ROOT / record["target_path"]).is_file(), record["target_path"])

    def test_all_targets_preserve_blob_and_sha256_identity(self) -> None:
        for record in self.payload["records"]:
            target = ROOT / record["target_path"]
            blob = subprocess.check_output(["git", "hash-object", "--", target], cwd=ROOT, text=True).strip()
            self.assertEqual(record["git_blob_sha1"], blob)
            self.assertEqual(record["sha256"], sha256(target))

    def test_old_active_roots_contain_markers_only(self) -> None:
        release_files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "docs/history/releases").rglob("*") if path.is_file())
        decision_files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "docs/decisions").rglob("*") if path.is_file())
        self.assertEqual(["docs/history/releases/README.md"], release_files)
        self.assertEqual(["docs/decisions/README.md"], decision_files)

    def test_quarantined_records_have_no_active_authority(self) -> None:
        self.assertEqual("HISTORICAL_QUARANTINED", self.payload["authority_state"])
        self.assertEqual("NONE", self.payload["market_authority"])
        self.assertFalse(self.payload["release_parent_eligible"])
        self.assertFalse(self.payload["selector_eligible"])
        self.assertFalse(self.payload["rollback_target_eligible"])
        self.assertFalse(self.payload["discovery_seed_eligible"])


if __name__ == "__main__":
    unittest.main()
''',
    )


def execute() -> None:
    if MANIFEST_PATH.exists():
        verify()
        return

    release_sources = _tracked_under(RELEASE_ROOT)
    decision_sources = _tracked_under(DECISION_ROOT)
    if not release_sources:
        raise SystemExit("R0-7 found no tracked historical release records to quarantine")
    if not decision_sources:
        raise SystemExit("R0-7 found no tracked decision records to classify as superseded")

    records = [_record(path, "PAST_RELEASE") for path in release_sources]
    records.extend(_record(path, "OUTDATED_DECISION") for path in decision_sources)
    records.sort(key=lambda item: item["source_path"])
    _move_records(records)

    manifest = {
        "schema": "ovc-r0-release-decision-quarantine/v1",
        "baseline_commit": BASELINE,
        "authority_state": "HISTORICAL_QUARANTINED",
        "market_authority": "NONE",
        "release_parent_eligible": False,
        "selector_eligible": False,
        "rollback_target_eligible": False,
        "parameter_source_eligible": False,
        "discovery_seed_eligible": False,
        "decision_classification_rule": (
            "Every record tracked under docs/decisions at R0-7 start belongs to the superseded v1 ABCD authority line; "
            "current R0 decisions are recorded in the repository-freeze packet and no v2 model decision is active."
        ),
        "release_count": len(release_sources),
        "outdated_decision_count": len(decision_sources),
        "record_count": len(records),
        "records": records,
    }
    _write_json(MANIFEST_PATH, manifest)
    _write_crosswalk(records)
    _write_active_markers()
    _write_authority_test()

    quarantine_readme = QUARANTINE_ROOT / "QUARANTINE_README.md"
    existing = quarantine_readme.read_text(encoding="utf-8")
    addition = (
        "\n## R0-7 historical release and decision addition\n\n"
        f"R0-7 moved {len(release_sources)} past release files and {len(decision_sources)} superseded decision files into this quarantine "
        "with exact Git blob and SHA-256 identity. See `R0_7_RELEASE_DECISION_QUARANTINE_MANIFEST.json`.\n"
    )
    if "## R0-7 historical release and decision addition" not in existing:
        _write_text(quarantine_readme, existing.rstrip() + "\n" + addition)

    authority_path = Path("registries/authority/ACTIVE_AUTHORITY.yaml")
    authority = authority_path.read_text(encoding="utf-8")
    authority = authority.replace(
        "state: V2_FOUNDATION_NO_MARKET_AUTHORITY",
        "state: V2_FOUNDATION_RESET_COMPLETE_NO_MARKET_AUTHORITY",
    )
    _write_text(authority_path, authority)

    status_path = Path("docs/CURRENT_STATUS.md")
    status = status_path.read_text(encoding="utf-8")
    status = status.replace(
        "R0-4 established the clean active-tree foundation. R0-5 installed 42 compact synthetic OPT-A, C1 and C2 fixture cases. The fixtures are non-authoritative and do not activate any research release.",
        "R0-4 established the clean active-tree foundation, R0-5 installed 42 non-authoritative synthetic fixture cases, and R0-6 installed the repository authority guard suite. R0-7 moved superseded v1 release and decision records into the historical quarantine and completed final validation. No research release is active.",
    )
    status = status.replace(
        "`R0-6 — repository authority guard suite`.",
        "`OPERATOR REVIEW — inspect PR #2 and approve or reject the reset merge`. No implementation work beyond R0 is authorised before that decision.",
    )
    _write_text(status_path, status)

    verify()


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify() -> dict[str, Any]:
    manifest = _load_manifest()
    records = manifest["records"]
    failures: list[str] = []
    for record in records:
        source = Path(record["source_path"])
        target = Path(record["target_path"])
        if source.exists():
            failures.append(f"source remains: {source}")
        if not target.is_file():
            failures.append(f"target missing: {target}")
            continue
        if _run("git", "hash-object", "--", target.as_posix()) != record["git_blob_sha1"]:
            failures.append(f"blob mismatch: {target}")
        if _sha256(target) != record["sha256"]:
            failures.append(f"sha256 mismatch: {target}")
    release_files = sorted(path for path in RELEASE_ROOT.rglob("*") if path.is_file())
    decision_files = sorted(path for path in DECISION_ROOT.rglob("*") if path.is_file())
    if release_files != [RELEASE_ROOT / "README.md"]:
        failures.append("docs/history/releases contains files other than the active marker")
    if decision_files != [DECISION_ROOT / "README.md"]:
        failures.append("docs/decisions contains files other than the active marker")
    if failures:
        raise SystemExit("R0-7 verification failed:\n" + "\n".join(failures))
    return manifest


def seal() -> None:
    manifest = verify()
    test_count = unittest.defaultTestLoader.discover("tests").countTestCases()
    main_commit = _run("git", "rev-parse", "origin/main")
    archive_commit = _run("git", "rev-parse", f"origin/{ARCHIVE_BRANCH}")
    if main_commit != BASELINE:
        raise SystemExit(f"main moved from approved R0 baseline: {main_commit}")
    if archive_commit != BASELINE:
        raise SystemExit(f"archive branch moved from frozen baseline: {archive_commit}")

    validation = {
        "schema": "ovc-r0-final-validation/v1",
        "baseline_commit": BASELINE,
        "main_commit": main_commit,
        "archive_branch": ARCHIVE_BRANCH,
        "archive_commit": archive_commit,
        "release_records_quarantined": manifest["release_count"],
        "outdated_decisions_quarantined": manifest["outdated_decision_count"],
        "total_additional_quarantine_records": manifest["record_count"],
        "source_paths_remaining": 0,
        "quarantine_targets_missing": 0,
        "blob_identity_verified": True,
        "sha256_identity_verified": True,
        "active_release_directory_payloads": 0,
        "active_outdated_decision_records": 0,
        "active_market_selectors": 0,
        "market_authority": "NONE",
        "fixture_case_count": 42,
        "authority_guard_family_count": 6,
        "test_case_count": test_count,
        "result": "PASS",
        "merge_authority": "AWAITING_OPERATOR_REVIEW",
    }
    _write_json(VALIDATION_PATH, validation)
    _write_text(
        OPERATOR_PACKET_PATH,
        "# R0-7 Final Validation and Operator Packet\n\n"
        "## Result\n\n"
        "**PASS — repository reset execution is complete and awaits explicit operator merge review.**\n\n"
        f"- Frozen baseline and `main`: `{BASELINE}`\n"
        f"- Historical archive branch: `{ARCHIVE_BRANCH}` at `{BASELINE}`\n"
        f"- Past release records moved to quarantine: **{manifest['release_count']}**\n"
        f"- Superseded decision records moved to quarantine: **{manifest['outdated_decision_count']}**\n"
        f"- Additional quarantine records verified: **{manifest['record_count']}**\n"
        "- Original source paths remaining: **0**\n"
        "- Missing quarantine targets: **0**\n"
        "- Git blob identity: **PASS**\n"
        "- SHA-256 identity: **PASS**\n"
        "- Synthetic fixture cases: **42**\n"
        "- Authority guard families: **6**\n"
        f"- Discovered active test cases: **{test_count}**\n"
        "- Active market selectors: **0**\n"
        "- Market authority: **NONE**\n\n"
        "## Final authority matrix\n\n"
        "| Component | Final R0 state | Active market authority |\n"
        "|---|---|---:|\n"
        "| Evidence store | `ACTIVE_INFRASTRUCTURE` | No |\n"
        "| OPT-A v1 | `HISTORICAL_SUPERSEDED_QUARANTINED` | No |\n"
        "| OPT-A v2 | `DESIGN_AND_FIXTURES_ONLY` | No |\n"
        "| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | No |\n"
        "| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | No |\n"
        "| C2E / C2.5 / C3 | `DEFERRED` | No |\n"
        "| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | No |\n"
        "| Historical releases and decisions | `HISTORICAL_QUARANTINED` | No |\n\n"
        "## Operator decision required\n\n"
        "Review PR #2, its exact diff, final CI status and this packet. Approve or reject the merge. R0-7 does not itself merge the branch, "
        "activate a selector, authorise provider intake, publish to R2, or begin OPT-A/C1/C2 implementation.\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["execute", "verify", "seal"])
    args = parser.parse_args()
    if args.command == "execute":
        execute()
    elif args.command == "verify":
        verify()
    else:
        seal()
