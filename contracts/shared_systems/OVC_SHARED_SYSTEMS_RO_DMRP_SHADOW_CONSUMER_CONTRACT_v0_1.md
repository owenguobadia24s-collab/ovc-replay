# Shared Systems Research Operations/DMRP Shadow Consumer Contract v0.1

Status: inactive read-only shadow contract. Authority effect: `NONE`.

This contract binds SHSI-WP8 to the existing `OVC-EC1-DMRP-CONFORMANCE-v0.1`
repository records without changing the programme's current binding. It does not
activate execution, append Research Operations records, consume Validation, fetch
real-source payloads, create an artifact store, or add a provider, source, or
research role.

## Exact consumption boundary

The governed fixture pins one synthetic corpus and one external-artifact binding
*metadata* manifest by repository path, SHA-256, and Git blob identity. The latter
is inspected as repository metadata only: referenced external bytes are neither
resolved nor fetched. The only provider is `REPOSITORY_GIT`; the only research
role is owner-declared `DISCOVERY`.

The consumption manifest is valid only when access remains `READ_ONLY`, operation
remains `SHADOW_ONLY`, the current binding is unchanged, no write is performed,
and no artifact store is created. A consumed provider, source, or role that is not
in its owner set is a typed hard failure.

## State, evidence, artifacts, and comparison

The state-plane crosswalk preserves the owner lifecycle literally. In particular,
`FROZEN` maps to lifecycle `FROZEN` and authority `UNKNOWN`; it never becomes an
authorization. Any non-unknown authority requires a separately supplied exact
owner decision reference, and this packet supplies none.

The evidence frontier accepts only the synthetic non-authoritative corpus. Missing
required record types produce `NOT_EVALUABLE` and `REQUIRED_RECORD_MISSING` rather
than invented evidence. Record logical identities cover the full owner record.

Local repository artifacts use the WP6 durable descriptor and reachability model.
Missing or corrupt bytes remain typed gaps. The shadow wrapper is a reversible
whole-record identity mapping; semantic invention and active adapters are
forbidden. Exact dual-run identity divergence blocks. Adapter complexity is
evaluated against the frozen WP6 pilot budget without slack.

## Rollback and authority

Rollback is removal of the inactive shadow-only bindings. This contract grants no
scientific, semantic, source, provider, research-role, Validation, candidate,
execution, publication, or write authority.
