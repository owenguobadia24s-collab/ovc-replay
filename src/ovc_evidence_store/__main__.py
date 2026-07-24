from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .manifest import EvidenceStoreError, build_manifest, load_manifest, verify_local
from .remote import upload, verify_remote


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

    put = commands.add_parser("upload", help="upload verified objects with rclone")
    put.add_argument("--manifest", type=Path, required=True)
    put.add_argument("--root", type=Path, required=True)
    put.add_argument("--remote", required=True)

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
        elif arguments.command == "upload":
            document = load_manifest(arguments.manifest)
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
