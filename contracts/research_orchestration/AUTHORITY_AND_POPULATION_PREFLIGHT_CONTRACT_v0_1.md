# IROF Authority and Population Preflight Contract v0.1

Status: INACTIVE ENGINEERING / READ-ONLY PREFLIGHT. Authority effect: NONE.

## Purpose

IROF may describe whether an already-declared profile can lawfully run against a PopulationSpec. It may not create, combine, consume or widen owner-programme authority. AuthorityBinding is evidence about an owner decision, never a grant emitted by IROF.

## Rules

1. Every StageSpec authority requirement resolves to one named owner programme, owner gate, authority kind and subject.
2. One binding must independently satisfy the entire required scope. Scope fragments from multiple bindings are never unioned.
3. A run-scoped or token-scoped requirement may require an unconsumed token, but IROF preflight only observes token state and never consumes it.
4. Owner authority for another programme or subject is reported separately and cannot satisfy a stage requirement. In particular, SRFDI-G-JUNE-AUTH v0.7 cannot satisfy C2E2-G6-RUN-AUTH.
5. Real source stages must declare an explicit owner authority requirement. Missing authority fails closed; no synthetic substitution or profile degradation is permitted.
6. A locked Validation population is denied before protected path, object, timestamp or row resolution. Logical protected release/manifest identities are omitted from the denial receipt.
7. Blocked stages and transitive blocked descendants are reported exactly from the canonical DAG. Already-materialised lawful ancestors may be reported as reusable evidence but do not authorize the blocked stage.
8. Preflight never activates selectors, boundary packs, scientific methods, publication, probability, risk, exposure, execution or agent-write authority.

## Current mandatory regression

At the WP3 court-record baseline, `FULL_DESCRIPTIVE` June real preflight must reach the current C2E owner boundary and return `NOT_AUTHORISED` because C2E2 real replay remains denied pending a fresh exact C2E2-G6 run authorization. The separately effective SRFD v0.7 single-run token must be visible as owner-programme authority, remain unused by IROF and remain unconsumed by this preflight.

## Rollback

Remove IROF authority resolver, registry, fixtures and tests. No owner-programme decision, token or source artifact is modified.
