# ESLI-WP13 G13 source-authority gate reproduction and rollback

No WP13 source rows have been read and no profile execution has started.

Reproduce the gate classification from repository court records by verifying: (1) WP12 completion/pointer to WP13; (2) `SRFD_JUNE_AUTHORITY_MANIFEST_R3.json` contains the exact accepted `C2_15M_BID_LOCAL` Drive ID/hash; (3) `SRFDI_WP10_V11_R3_POSTRUN_RECONCILIATION.json` records the prior token as `CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN`; and (4) no current repository authority record grants ESLI-WP13 a reusable read of that external artifact.

If the operator DEFERs or BLOCKs, leave the source unread and preserve this packet append-only. If PASS is later superseded before read, do the same. After any authorised read, failures are corrected forward; accepted June source evidence and prior SRFD evidence are never rewritten.
