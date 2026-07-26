# Research CLI and Append-Only Service Contract v0.1

Status: `FROZEN_AFTER_RO_WP2`

The `ovc` Research Operations command surface is the only operator write boundary introduced by RO-WP2. It creates derived drafts under `var/research_operations/` and compact frozen records under `records/research_operations/`.

Every public write action emits a frozen `AuditEvent`. Frozen records are created with exclusive-write semantics and cannot be overwritten, renamed to reuse identity, or deleted through the service. Corrections create a successor whose `lineage.supersedes` points to the immutable predecessor.

The command families are:

```text
ovc research ...
ovc artifact ...
ovc queue ...
```

The service may create or freeze Research Operations records, scan approved roots, verify declared artifacts, emit reports, and show queues. It may not invoke Git commit or push, provider downloads, R2 upload or deletion, selector or threshold mutation, model classification, Validation payload access, probability, exposure, trading, execution, or agent actions.

RO-WP2 implementation is not active-research authority. Activation remains gated by RO-G2 and later RO-G3.
