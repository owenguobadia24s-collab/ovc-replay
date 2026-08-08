# SRFDI-WP2D v0.2 Source and June Binding Correction Contract v0.1

## Status

Corrective, additive and non-scientific. This packet is inside the already-approved SRFD implementation plan and the operator-frozen `SRFDI-G9S-FREEZE` v0.2 preregistration envelope.

## Purpose

Materialise versioned implementation surfaces needed to bind the exact frozen v0.2 preregistration to the already-accepted June replay source before the separately operator-reserved `SRFDI-G-JUNE-AUTH` gate.

The historical `source_adapter.py` and `june_authority.py` remain immutable v0.1 evidence. This packet adds `source_adapter_v02.py` and `june_authority_v02.py`; it does not silently rewrite the historical verifier or source adapter.

## Triggering defect

The accepted frozen June C2 payload can retain an optional descriptive `reason_code` on an axis whose `status` remains `EVALUATED`, notably the QUALITY axis. The WP2C source contract requires the adapter to preserve axis `status`, `value`, `reason_code` and `measurement` exactly and does not define a descriptive reason on an evaluated axis as a computability failure.

The historical adapter rejects that exact shape. The v0.2 adapter therefore:

- preserves the optional descriptive reason without rewriting it;
- continues to require a reason for any non-`EVALUATED` axis;
- continues to derive computability from axis status, not from descriptive reason presence;
- preserves the logical hash of the original source row;
- preserves target membership from independently reproduced parent-C1 `open_time` classification;
- preserves the exact five-axis schema and all existing lineage/authority firewalls.

No category, threshold, family, distance, sensitivity, candidate or scientific result is promoted by this correction.

## Frozen v0.2 authority bindings

The v0.2 June verifier is bound to:

- preregistration ID `OVC-SRFD-JUNE-PREREG-v0.2-CANDIDATE`;
- preregistration byte/logical SHA-256 `13c17cf64c576b35e53047de753a5fd1a49bbdc7205c387bbcedb5a34441b804`;
- prerequisite gate `SRFDI-G9S-FREEZE`;
- representation-pack registry byte/logical SHA-256 `7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0`;
- representation-pack registry path `registries/research/srfd/real_source_representation_packs_v0_2.json`.

The verifier must also bind an exact source release, source commit, source slice, source/output manifest hashes, source-record hash aggregate, population ID/counts/ID hashes/exclusion hash, implementation commit and dependency-manifest hash before it can emit any authority token.

## Operator boundary

This packet does **not** grant June execution. `june_authority_v02.verify_june_run_authority()` fails closed unless an immutable operator decision at `SRFDI-G-JUNE-AUTH` has decision `AUTHORIZE_JUNE` and binds the exact candidate manifest hash.

Even after that future decision, the verifier requires:

- provider fetch `DENIED` / `FORBIDDEN`;
- upstream mutation `FORBIDDEN`;
- Validation 2025 `LOCKED_UNCONSUMED`;
- selector change `NONE`;
- scientific promotion `NONE`;
- publication `NONE`;
- probability/risk/exposure/execution `NONE`.

## Dependency boundary

No new runtime dependency is admitted. The corrective implementation is Python stdlib plus existing OVC modules only. The exact dependency manifest is `docs/releases/srfd-benchmark-v0-1/srfdi-wp2d/SRFDI_WP2D_DEPENDENCY_MANIFEST.json`, logical SHA-256 `88ad3ec673493cb82b6b6d4fda90c077535e88d9f630a0535d56df887944ae3f`.

## Acceptance

The corrective packet passes only if:

1. historical v0.1 modules remain unchanged;
2. synthetic assurance proves the historical rejection and v0.2 preservation of an evaluated descriptive reason;
3. v0.2 population binding remains deterministic and order-independent;
4. v0.2 authority verification binds exact preregistration and pack-registry hashes;
5. no operator decision means no June token;
6. repository-wide and final-head assurance pass;
7. no raw market data is committed;
8. no reserved authority changes.

## Rollback

Revert or abandon only the additive WP2D files. Historical v0.1 evidence and the operator-frozen v0.2 preregistration remain intact. Never force-push, rewrite history, fetch a provider, consume Validation or execute June as part of rollback.
