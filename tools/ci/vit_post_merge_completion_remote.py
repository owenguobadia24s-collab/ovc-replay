#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import ReceiptStore
from tools.ci import vit_post_merge_completion as legacy
from tools.ci import vit_post_merge_completion_late_binding as late


LEGACY_LINEAGE_ENV = "OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE"


def _recover_explicit_historical_request(*, repo_root: Path, merge_sha: str, receipt_store: ReceiptStore) -> None:
    """Recover one manifest-listed historical transaction without weakening forward admission.

    Detached exact-head qualification remains mandatory for the primary/current merge.
    A merge SHA explicitly present in the recovery manifest is a historical recovery
    request, so it may use the already-existing PR-body lineage migration route.
    The opt-in is scoped to exactly this call and the prior environment value is restored.
    """
    previous = os.environ.get(LEGACY_LINEAGE_ENV)
    os.environ[LEGACY_LINEAGE_ENV] = "true"
    try:
        late._recover_one(repo_root=repo_root, merge_sha=merge_sha, receipt_store=receipt_store)
    finally:
        if previous is None:
            os.environ.pop(LEGACY_LINEAGE_ENV, None)
        else:
            os.environ[LEGACY_LINEAGE_ENV] = previous


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

        # The current/primary merge is never allowed to fall back to PR-body lineage.
        late._recover_one(repo_root=repo_root, merge_sha=args.merge_sha, receipt_store=receipt_store)

        # Explicit manifest rows are historical recovery/migration requests. De-duplicate
        # the primary merge and use the pre-existing, tightly scoped legacy-lineage route
        # only while each historical request is being reconstructed.
        seen = {args.merge_sha}
        for merge_sha in late._manifest_requests(recovery_path):
            if merge_sha in seen:
                continue
            seen.add(merge_sha)
            _recover_explicit_historical_request(
                repo_root=repo_root,
                merge_sha=merge_sha,
                receipt_store=receipt_store,
            )
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
