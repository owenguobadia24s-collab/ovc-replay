# MG CEAR-G10 Candidate Migration and Ablation Contract v0.1

**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP7`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` only.

## Purpose

Migrate the fourteen CEAR-G10 rule candidates from the legacy frequency-conjunction
representation into a typed, domain-separated comparison ledger. The migration is
diagnostic and traceability-preserving. It does not promote a candidate, create a
canonical grammar, activate a selector, publish a release or grant C3/Validation/
probability/risk/exposure/execution authority.

## Frozen source evidence

The packet reads only the accepted CEAR-G10 evidence family:

- `CEAR_G10_DISPOSITION_EVIDENCE.json` — Drive file
  `1xffbDKFIGEK8MLNH-eh3UdhBueASHTU4`, raw SHA-256
  `6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944`;
- `rule-candidates.jsonl` — Drive file
  `1rVbwRC_fD7SIO_XmZd_OCBppudKrQ0_6`, raw SHA-256
  `db9966224abd75619971bbdbff40e078e955ee5b933fa82416ceab2048521230`;
- `functional-cores.json` — Drive file
  `1rvuaLZ82IzcAInejQRExWJ_V5_i61dRy`, raw SHA-256
  `77f9ee2a58d5d8b9fcf0eb43cf20a9cef4c69ba8c2fe8750a6a04d123a2f1bae`.

Git retains a compact feature-migration registry, one source-hash-bound record per candidate, and a ledger index required to reproduce and review the migration. The external source artifacts remain authoritative for their own bytes.

## Migration semantics

`MAPPED` means every source clause has been accounted for in a typed domain and usage.
It does **not** mean semantic equivalence, empirical match-set parity, candidate promotion
or grammar canonisation.

Each source clause is assigned exactly one domain:

- `STRUCTURAL`
- `TEMPORAL`
- `OBJECT_BINDING`
- `CONTEXT`
- `COMPUTABILITY`
- `PROVENANCE`

Every mapped clause is also assigned one typed usage. `PROVENANCE` clauses are
`DIAGNOSTIC_ONLY_PROVENANCE`; `COMPUTABILITY` clauses are guards. Neither may become a
structural grammar predicate.

The CEAR-G10 flattened AST includes indexed legacy arrays such as `context_ids[n]` and
`object_ids[n]`. Their treatment here is a migration adapter for this frozen source
format, not an amendment to the MG-WP1 predicate-domain registry.

## Legacy classification preservation

For each candidate the ledger retains:

- source candidate, functional-core and family IDs;
- full legacy functional-core classification counts;
- per-candidate legacy classification counts plus source-clause inventory and typed-mapping hashes;
- the exact clause-level source remains hash-bound in the accepted external source artifacts;
- source rule hash;
- evaluation population, outcomes, match/counterexample counts and hashes.

Legacy `CONTRADICTORY` frequency classifications are not re-labelled as
`LOGICAL_CONFLICT`. An exact logical conflict requires a matching frozen exclusivity rule
under the same typed object, clock and first-valid scope. None of the fourteen migrated
candidate clause surfaces satisfies such a proof in this packet.

## Frequency-conjunction comparison

The legacy rule form is an `ALL_OF` conjunction of measurement comparisons. WP7 records
a typed predicate inventory and clause-domain ablation. It does not claim empirical
match-set parity after removing provenance/computability conditions because removing a
conjunct can lawfully enlarge a match set.

The comparison therefore reports:

- original clause count;
- typed domain and layer counts;
- provenance clause count;
- computability guard count;
- source match and counterexample hashes;
- exact empirical parity as `NOT_EVALUATED_IN_WP7`.

Any later empirical typed-grammar comparison requires a separately bounded replay or the
MG-WP8 topology smoke where the source records are reproducible.

## Determinism

The migration ID and ledger SHA-256 are computed from canonical UTF-8 JSON with sorted
keys and no environment fields. Candidate input order must not change the ledger.

## Prohibitions

- candidate, rule, family or grammar promotion;
- canonical sensitivity/family/grammar selection;
- selector activation or replacement;
- C3 semantic handoff;
- publication or R2 write;
- Active Discovery, Development or Validation;
- outcome/future-path inputs into migration;
- probability, eligibility, risk, exposure or execution.

## Rollback

Remove or supersede the inactive migration implementation and compact ledger while
preserving all source evidence hashes, CEAR-G10 decisions and previously completed MG
packets. No historical source artifact is rewritten.
