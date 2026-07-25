# A2-G0 — OPT-A v2 Foundation Review

## Review identity

- Gate: `A2-G0-FOUNDATION-REVIEW`
- Programme: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2`
- Repository: `owenguobadia24s-collab/ovc-replay`
- Reviewed `main` commit: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- Review branch: `review/opt-a-v2-a2-g0-foundation`
- Review date: 25 July 2026

## Predecessor integration

| Work packet | Merged commit | Gate result | Review finding |
|---|---|---|---|
| R0 reset | `a9902c97e21131b1882b4c11ca3a2a79273e7c77` | PASS | Historical executable and release authority quarantined; clean active tree retained |
| WP1 release governance | `5c567c1ba7de57d83079200c006f991d41642310` | PASS | v1 disposition and exact v2 role identities frozen |
| WP2 evidence lifecycle | `91d57980be84239de69de00c43649d20a2acd7fe` | PASS | External-root, workspace, freeze, approval and readiness controls implemented |
| WP3 provider/clock/handoff | `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d` | PASS | Provider, source-object, UTC clock, role split, reconciliation and handoff contracts frozen |

The reviewed `main` tip is exactly the WP3 merge commit and therefore includes WP1, WP2 and WP3.

## Gate criteria and findings

| Criterion | Required state | Finding |
|---|---|---|
| G0-01 programme identity | GBPUSD, Dukascopy, `[2021-01-01, 2026-01-01)`, M1/H1, BID/ASK | PASS |
| G0-02 historical v1 disposition | `SUPERSEDED_UNPUBLISHED`, unavailable, no identifier reuse or fallback | PASS |
| G0-03 role releases | discovery 2021–2023, development 2024, validation 2025, non-overlapping | PASS |
| G0-04 selector and validation controls | every selector `NONE`; validation `LOCKED_UNCONSUMED` and default deny | PASS |
| G0-05 evidence lifecycle | process-only external root, deterministic inventory, gated freeze, approval-bound upload, read-only readiness | PASS |
| G0-06 source-object contracts | monthly M1 BID/ASK and H1 BID/ASK identities with exact byte and schema binding | PASS |
| G0-07 clock and aggregation | UTC half-open intervals, A–L 2H spine, exact parent sets, no fill, no hidden H1 substitution | PASS |
| G0-08 reconciliation and handoff | native/derived H1 remain distinct; one-way sealed handoff to OPT-B.C1 only | PASS |
| G0-09 synthetic fixtures | contract fixtures are synthetic, non-authoritative and denied as seeds/releases/selectors | PASS |
| G0-10 repository authority | no active market selector, no active handoff, no raw market population in Git | PASS |
| G0-11 integrated CI | complete merged foundation plus A2-G0 review guards | PASS — 100 tests, 0 failures, 0 errors |

Canonical pre-seal CI evidence:

- tested head: `b735266c9ef8200a825d1a6e19e9c8de2d202417`
- tested PR merge commit: `6b3eddbb1df567d00d007d64e6fe67012a9b795f`
- workflow run: `30173948121`
- command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

The PR must remain green after the final state-sealing edits before merge.

## Foundation decision

**PASS.** The repository foundation is technically and governably coherent for the next OPT-A v2 execution packet.

A2-G0 clears the programme-level block that prevented the next provider-intake packet from beginning. It authorises **WP4 provider-intake implementation and bounded provider execution only after the operator-local preflight below passes**. It does not itself download any provider bytes.

## Mandatory operator-local preflight before the first provider request

GitHub Actions cannot inspect the operator's Windows filesystem or environment-only credentials. Before the first provider request, the WP4 operator run must record all of the following:

1. `OVC_EXTERNAL_ARTIFACT_ROOT` resolves to an existing operator-controlled directory outside the Git worktree.
2. The external root passes repository-disjointness, symlink and path-traversal checks.
3. A new immutable workspace identity can be created without overwriting an existing workspace or release.
4. Sufficient local capacity is recorded for the planned monthly source-object population and derived workspaces.
5. Provider configuration contains no secret or machine-specific path in Git.
6. The configured R2 remote and `ovc-evidence` bucket are checked read-only and the required canonical lock visibility is recorded before any later publication approval.
7. Every readiness result that cannot be evaluated is recorded as `NOT_EVALUATED`; it must not be silently treated as PASS.

Failure of items 1–5 blocks the first provider request. Item 6 blocks canonical publication, not local intake, unless the later WP4 execution plan explicitly elevates it to an intake prerequisite.

## Authority after merge

Permitted:

- implement the governed Dukascopy intake client and parser;
- create a fresh external workspace;
- perform a bounded synthetic/provider connectivity pilot;
- begin monthly GBPUSD M1/H1 BID/ASK acquisition after local preflight;
- create intake records, source-object identities, inventories and QA records outside Git;
- commit compact code, contracts, schemas, manifests, summaries and decisions.

Still prohibited:

- treating mutable workspace bytes as a release;
- canonical R2 publication without exact publication approval and full readiness;
- activating any OPT-A selector;
- consuming the 2025 validation population for design or threshold selection;
- activating the OPT-A-to-OPT-B handoff;
- using historical v1 as fallback, rollback target or parameter source;
- issuing OPT-B/C/D semantic, probability, exposure, trading or execution authority.

## Review conclusion

`A2-G0` is sealed as `PASS` and awaits operator review and merge. The decision introduces governance authority for the next bounded intake packet, not market authority.