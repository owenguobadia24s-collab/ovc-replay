from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .external_root import resolve_external_root
from .lifecycle import (
    build_workspace_inventory,
    freeze_release,
    load_publication_approval,
    load_workspace_inventory,
    validate_identifier,
    write_workspace_inventory,
)
from .manifest import EvidenceStoreError, build_manifest, load_manifest, verify_local
from .readiness import publication_readiness
from .remote import upload, verify_remote


def _repository_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ovc_evidence_store")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build a deterministic release manifest")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--release-id", required=True)
    build.add_argument("--manifest-id", required=True)
    build.add_argument("--bucket", required=True)
    build.add_argument("--prefix", required=True)
    build.add_argument("--authority-state", required=True)
    build.add_argument("--repository-commit", required=True)
    build.add_argument("--source-ref", required=True)

    local = commands.add_parser("verify-local", help="fully verify local release bytes")
    local.add_argument("--manifest", type=Path, required=True)
    local.add_argument("--root", type=Path, required=True)

    workspace = commands.add_parser(
        "init-workspace",
        help="create a safe mutable workspace under OVC_EXTERNAL_ARTIFACT_ROOT",
    )
    workspace.add_argument("--workspace-id", required=True)
    _repository_argument(workspace)

    inventory = commands.add_parser(
        "inventory-workspace",
        help="write a deterministic workspace inventory outside the workspace",
    )
    inventory.add_argument("--workspace-id", required=True)
    inventory.add_argument("--output", type=Path, required=True)
    _repository_argument(inventory)

    freeze = commands.add_parser(
        "freeze-release",
        help="promote an exact approved workspace inventory into a new release root",
    )
    freeze.add_argument("--workspace-id", required=True)
    freeze.add_argument("--release-id", required=True)
    freeze.add_argument("--qa-state", required=True)
    freeze.add_argument("--inventory", type=Path, required=True)
    _repository_argument(freeze)

    ready = commands.add_parser(
        "readiness",
        help="run non-destructive local, Git and optional remote readiness checks",
    )
    ready.add_argument("--manifest", type=Path, required=True)
    ready.add_argument("--root", type=Path, required=True)
    ready.add_argument("--approval", type=Path, required=True)
    ready.add_argument("--remote")
    ready.add_argument(
        "--bucket-lock-visible",
        choices=("true", "false", "unknown"),
        default="unknown",
    )
    _repository_argument(ready)

    put = commands.add_parser(
        "upload",
        help="upload verified objects with rclone after exact publication approval",
    )
    put.add_argument("--manifest", type=Path, required=True)
    put.add_argument("--root", type=Path, required=True)
    put.add_argument("--remote", required=True)
    put.add_argument("--approval", type=Path, required=True)

    remote = commands.add_parser("verify-remote", help="read back and verify remote objects")
    remote.add_argument("--manifest", type=Path, required=True)
    remote.add_argument("--remote", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "build":
            document = build_manifest(
                root=arguments.root,
                output=arguments.output,
                release_id=arguments.release_id,
                manifest_id=arguments.manifest_id,
                bucket=arguments.bucket,
                prefix=arguments.prefix,
                authority_state=arguments.authority_state,
                repository_commit=arguments.repository_commit,
                source_ref=arguments.source_ref,
            )
            print(f"wrote {arguments.output} with {len(document['files'])} file(s)")
        elif arguments.command == "verify-local":
            document = load_manifest(arguments.manifest)
            verify_local(document, arguments.root)
            print(f"verified {len(document['files'])} local file(s)")
        elif arguments.command == "init-workspace":
            external = resolve_external_root(
                repository_root=arguments.repository_root,
                create=True,
            )
            from .lifecycle import init_workspace

            path = init_workspace(external, arguments.workspace_id)
            print(path)
        elif arguments.command == "inventory-workspace":
            external = resolve_external_root(
                repository_root=arguments.repository_root,
            )
            workspace_id = validate_identifier(arguments.workspace_id, "workspace-id")
            workspace_path = external / "workspace" / workspace_id
            document = build_workspace_inventory(workspace_path, workspace_id)
            output = arguments.output.resolve()
            try:
                output.relative_to(workspace_path.resolve())
            except ValueError:
                pass
            else:
                raise EvidenceStoreError("workspace inventory output must be outside the workspace")
            write_workspace_inventory(output, document)
            print(f"wrote {output} with {len(document['files'])} file(s)")
        elif arguments.command == "freeze-release":
            external = resolve_external_root(
                repository_root=arguments.repository_root,
            )
            inventory = load_workspace_inventory(arguments.inventory)
            release, receipt_path, receipt = freeze_release(
                external_root=external,
                workspace_id=arguments.workspace_id,
                release_id=arguments.release_id,
                qa_state=arguments.qa_state,
                inventory=inventory,
            )
            print(
                f"froze {release} with {receipt['file_count']} file(s); "
                f"receipt={receipt_path}"
            )
        elif arguments.command == "readiness":
            lock_state = {
                "true": True,
                "false": False,
                "unknown": None,
            }[arguments.bucket_lock_visible]
            result = publication_readiness(
                release_root=arguments.root,
                manifest_path=arguments.manifest,
                approval_path=arguments.approval,
                repository_root=arguments.repository_root,
                remote=arguments.remote,
                bucket_lock_visible=lock_state,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            if result["overall_status"] == "BLOCKED":
                return 1
        elif arguments.command == "upload":
            document = load_manifest(arguments.manifest)
            load_publication_approval(
                arguments.approval,
                manifest=document,
                manifest_path=arguments.manifest,
            )
            upload(document, arguments.manifest, arguments.root, arguments.remote)
            print(f"uploaded {len(document['files'])} file(s) and manifest")
        elif arguments.command == "verify-remote":
            document = load_manifest(arguments.manifest)
            verify_remote(document, arguments.manifest, arguments.remote)
            print(f"verified {len(document['files'])} remote file(s) and manifest")
        return 0
    except EvidenceStoreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
