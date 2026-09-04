#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import ReceiptStore
from tools.ci import vit_post_merge_completion as legacy
from tools.ci import vit_post_merge_completion_late_binding as late


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--merge-sha", required=True)
    parser.add_argument("--receipt-store-root", required=True)
    parser.add_argument("--recovery-manifest")
    args = parser.parse_args()
    try:
        repo_root = Path(args.repo_root).resolve()
        receipt_root = Path(args.receipt_store_root).resolve()
        receipt_store = ReceiptStore(receipt_root)
        recovery_path = Path(args.recovery_manifest).resolve() if args.recovery_manifest else None
        requested = [args.merge_sha, *late._manifest_requests(recovery_path)]
        seen: set[str] = set()
        queue = [sha for sha in requested if not (sha in seen or seen.add(sha))]
        for merge_sha in queue:
            late._recover_one(repo_root=repo_root, merge_sha=merge_sha, receipt_store=receipt_store)
        return 0
    except (
        legacy.PostMergeCompletionError,
        VitContractError,
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(
            "::error title=DSAI3V remote post-merge completion failed::"
            f"OVC_VIT_REMOTE_POST_MERGE_COMPLETION_FAILED: {exc}",
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
