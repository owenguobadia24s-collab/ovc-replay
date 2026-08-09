from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis.topology import (
    build_repository_topology,
    canonical_json_bytes,
    canonical_sha256,
    compact_topology_summary,
)


DEFAULT_RULE_PACK = Path("registries/governance/genesis_repository_topology/GRT_TOPOLOGY_RULE_PACK_v0_1.json")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def build_outputs(repository_root: Path, *, ref: str, output_dir: Path, verify_determinism: bool) -> dict[str, Any]:
    rule_path = repository_root / DEFAULT_RULE_PACK
    rule_pack = _load_json(rule_path)
    first = build_repository_topology(repository_root, ref=ref, rule_pack=rule_pack)
    second_sha = first["topology_sha256"]
    second_diagnostics: dict[str, Any] | None = None
    if verify_determinism:
        second = build_repository_topology(repository_root, ref=ref, rule_pack=rule_pack)
        second_sha = second["topology_sha256"]
        second_diagnostics = dict(second.get("diagnostics", {}))
        if second_sha != first["topology_sha256"]:
            raise SystemExit("GRT deterministic rebuild failed: topology identities differ")

    summary = compact_topology_summary(first)
    manifest = {
        "schema": "ovc-genesis-repository-topology-build-manifest/v1",
        "programme_id": "OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1",
        "packet_id": "GRT-WP7",
        "source_commit": first["portfolio"]["source_commit"],
        "rule_pack_id": rule_pack["rule_pack_id"],
        "rule_pack_sha256": canonical_sha256(rule_pack),
        "topology_sha256": first["topology_sha256"],
        "determinism": {
            "clean_rebuild_runs": 2 if verify_determinism else 1,
            "first_topology_sha256": first["topology_sha256"],
            "second_topology_sha256": second_sha,
            "result": "PASS" if second_sha == first["topology_sha256"] else "FAIL",
        },
        "counts": {
            "programmes": first["portfolio"]["programme_count"],
            "components": first["portfolio"]["component_count"],
            "component_edges": first["portfolio"]["component_edge_count"],
            "programme_dependencies": first["portfolio"]["programme_dependency_count"],
            "anomalies": first["portfolio"]["anomaly_count"],
        },
        "performance": {
            "first": first.get("diagnostics", {}),
            "second": second_diagnostics,
        },
        "authority_effect": "NONE_DERIVED_BUILD_EVIDENCE",
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)

    _write_json(output_dir / "GENESIS_REPOSITORY_TOPOLOGY_READ_MODEL.json", first)
    _write_json(output_dir / "GRT_TOPOLOGY_COMPACT_SUMMARY.json", summary)
    _write_json(output_dir / "GRT_TOPOLOGY_BUILD_MANIFEST.json", manifest)
    return {"read_model": first, "summary": summary, "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the authority-neutral Genesis Repository Topology read model.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output-dir", default="var/governance/genesis_repository_topology/current")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    repository_root = Path(args.repository_root).resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repository_root / output_dir
    result = build_outputs(repository_root, ref=args.ref, output_dir=output_dir, verify_determinism=args.verify_determinism)
    print(json.dumps({
        "topology_sha256": result["read_model"]["topology_sha256"],
        "programmes": result["manifest"]["counts"]["programmes"],
        "components": result["manifest"]["counts"]["components"],
        "component_edges": result["manifest"]["counts"]["component_edges"],
        "anomalies": result["manifest"]["counts"]["anomalies"],
        "determinism": result["manifest"]["determinism"]["result"],
        "authority_effect": "NONE_DERIVED_BUILD_EVIDENCE",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
