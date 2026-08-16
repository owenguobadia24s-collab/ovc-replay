# OVC Operator-Reserved Authority Gate Doctrine v0.1

Status: RATIFIED / OPERATOR PASS 2026-08-16T00:53:00+01:00
Authority effect: FORWARD GOVERNANCE SEMANTICS; implementation/migration only inside this doctrine
Primary principle: OVC is recursively autonomous inside granted authority and human-governed at genuine authority boundaries.

## 0. Executive decision

OVC SHALL classify gates by the net-new authority delta of the exact proposed PASS effect, not by gate name, ordinal, historical label, difficulty, packet completion, review status, PR readiness or the mere fact that a human could inspect the work.

The controlling question is:

> Would PASS at this exact gate instance grant, change, select, activate, publish, expose, destroy, waive or otherwise exercise authority that is not already contained inside the current effective AuthorityEnvelope?

If NO, the gate is mechanical/review work inside existing authority and SHALL proceed without operator confirmation once its exact acceptance, QA, review and rollback prerequisites are satisfied.

If YES, OVC SHALL complete every lawful mechanical prerequisite first, materialize one consolidated decision packet, and stop once for the operator.

Human governance and human verification are distinct. The operator sets direction, authority and tempo. The operator is not the default code reviewer, QA verifier, branch manager, CI supervisor, merge clerk, deterministic test oracle, retry controller or implementation-conformance inspector.

## 1. Gate taxonomy

Every gate SHALL expose two orthogonal fields:

- `gate_function`: `ASSURANCE | REVIEW | AUTHORITY_DECISION | MIXED`
- `execution_class`: `AUTO_RATIFIABLE | REVIEW_PREREQUISITE | OPERATOR_REQUIRED | BLOCKED | HARD_DENY`

### 1.1 ASSURANCE

Asks whether already-authorised work conforms to already-authorised requirements. This includes contract/schema conformance, deterministic fixtures, replay equivalence, reference/optimized equivalence, regression tests, QA, lineage integrity, restart equivalence, performance inside an authorised budget and bounded shadow comparison already granted by the current envelope.

Default execution class: `AUTO_RATIFIABLE`.

### 1.2 REVIEW

Requires qualified human, source-owner or independent judgment but does not itself grant new authority. Examples include independent algorithmic review, adversarial review, semantic-conformance review and non-activating usability assessment.

Default execution class: `REVIEW_PREREQUISITE`.

`REVIEW_PREREQUISITE != OPERATOR_REQUIRED`.

### 1.3 AUTHORITY_DECISION

Asks whether OVC may cross a new authority frontier. It is `OPERATOR_REQUIRED` only when the exact predicate in §4 evaluates true.

### 1.4 MIXED

A mixed gate SHALL complete and repair all mechanical work before the stop. The operator is asked only about the unresolved net-new authority delta.

## 2. AuthorityEnvelope

Every operator decision that authorises future work SHOULD materialize an exact `AuthorityEnvelope` containing at minimum:

- `envelope_id`, governing plan/version, operator decision reference and effective time;
- mandate: programme IDs, objectives and authorised successor sequence;
- scope: instruments, markets, providers, sides, clocks, populations, source generations and protected dependencies;
- research roles and execution modes;
- allowed and prohibited capabilities;
- scientific, semantic, publication, governance and write authority;
- resource/tempo envelope: compute, concurrency, storage, checkpoint, external-cost and escalation bounds;
- reserved successor boundaries and terminal/expiry condition.

A later gate SHALL be evaluated against the current effective envelope. A historically reserved action does not require a second operator stop when the exact action is already contained in that envelope.

## 3. Authority delta

For gate instance `G`:

```
A0 = exact current AuthorityEnvelope
P  = exact proposed PASS effect of G
A1 = apply(A0, P)
ΔA = canonical_diff(A0, A1)
```

The gate class derives from `ΔA`. Gate number, title, historical convention, finality, perceived risk or implementation difficulty are non-authoritative metadata.

## 4. Exact OPERATOR_REQUIRED predicate

```
CLASSIFY_GATE(G):
    if constitutional_hard_deny(G):
        return HARD_DENY
    if required_authority_or_source_is_missing(G):
        return BLOCKED
    if proposed_pass_effect_is_not_machine_resolvable(G):
        return BLOCKED

    ΔA = canonical_authority_delta(G)

    if requires_reserved_authority(ΔA):
        return OPERATOR_REQUIRED
    if requires_authoritative_discretion(G):
        return OPERATOR_REQUIRED
    if required_independent_or_human_review_remains(G):
        return REVIEW_PREREQUISITE
    if acceptance_conditions_pass(G)
       and QA == PASS
       and no_blocking_issue
       and rollback_is_defined:
        return AUTO_RATIFIABLE
    return BLOCKED
```

Normatively:

```
OPERATOR_REQUIRED(G) :=
    NOT HARD_DENY(G)
    AND NOT BLOCKED_UNRESOLVED(G)
    AND (
        EXISTS d IN ΔA :
            RESERVED_DELTA(d)
            AND NOT ALREADY_GRANTED(d, CURRENT_AUTHORITY_ENVELOPE)
        OR AUTHORITATIVE_DISCRETION_REQUIRED(G)
    )
```

## 5. Reserved delta catalogue

A proposed PASS effect is operator-reserved only when it creates a net-new, not-already-delegated instance of one of these deltas:

1. `OPR.MANDATE_CHANGE` — create/replace/materially redirect a programme mandate or governing objective.
2. `OPR.SCOPE_EXPANSION` — add an undelegated instrument, market, provider, side, clock, source generation, population, protected dependency, research role or consequential integration surface.
3. `OPR.REAL_SOURCE_TRANSITION` — first transition from fixture/synthetic/historical/rehearsal/shadow into real-source evidentiary consumption or durable evidentiary production beyond the envelope.
4. `OPR.ACTIVATION` — first material transition such as INACTIVE→ACTIVE, SHADOW→ACTIVE, ADVISORY→CONTROLLING, OBSERVING→BLOCKING, REFERENCE_ONLY→PRODUCTION, READ_ONLY→WRITE_CAPABLE or NONCANONICAL→CANONICAL.
5. `OPR.SCIENTIFIC_PROMOTION` — freeze/select/promote a ResearchCandidateGeneration, theory, model, method, representation, normalization, distance, family, topology, sensitivity regime, scientifically meaningful threshold, semantic term, event vocabulary, grammar or comparator.
6. `OPR.RESEARCH_ROLE` — new ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT, ACTIVE_VALIDATION, protected Validation access/consumption or irreversible protected-role information exposure.
7. `OPR.GOVERNANCE_CHANGE` — change repository-law semantics, authority semantics, ownership cardinality, governance owner, current/historical boundary, exception semantics, enforcement semantics, source precedence or a frozen constitutional contract.
8. `OPR.OWNER_CHOICE` — choose between conflicting lawful authoritative owners/claims.
9. `OPR.FROZEN_CONTRACT_CHANGE` — materially change frozen semantics. Correcting an implementation defect back into conformance does not count.
10. `OPR.WRITE_AUTHORITY` — first grant of agent/governance/external mutation/merge/enforcement/automatic actuation capability not already delegated.
11. `OPR.PUBLICATION` — canonical/R2 publication or a new operator-governed immutable publication identity.
12. `OPR.EXPOSURE` — new probability, E-H, risk, exposure, trade-permission, entry/exit or execution authority.
13. `OPR.DESTRUCTIVE` — permitted-but-reserved deletion, destructive migration, irreversible retirement/data loss or history alteration; constitutionally prohibited actions remain HARD_DENY.
14. `OPR.TEMPO_EXPANSION` — materially expand external cost, compute tier, concurrency, storage or long-running execution beyond the current resource/tempo envelope.
15. `OPR.OVERRIDE` — waive or override a normally blocking invariant.
16. `OPR.AUTHORITATIVE_DISCRETION` — choose among multiple lawful alternatives where the choice itself would become canonical/active/authoritative, determine whether evidence justifies scientific promotion, grant a capability activation, resolve governance-owner conflict, grant an invariant exception, materially redirect purpose or set a new operator-owned direction/tempo envelope.

## 6. Human review is not operator authority

These states SHALL remain distinct:

- `MACHINE_ASSURANCE_REQUIRED`
- `INDEPENDENT_REVIEW_REQUIRED`
- `SOURCE_OWNER_REVIEW_REQUIRED`
- `HUMAN_REVIEW_REQUIRED`
- `OPERATOR_REQUIRED`

A qualified reviewer may determine whether evidence satisfies a frozen requirement. The operator decides whether new authority should exist. Missing source truth SHALL produce `BLOCKED`, `UNRESOLVED` or `SOURCE_OWNER_REVIEW_REQUIRED`; the operator is not a fallback oracle for absent source authority.

## 7. Recursive delegation

An operator-required gate SHOULD grant the widest exact downstream envelope that the decision actually intends. Once granted, every successor action contained in that envelope becomes execution rather than repeated governance.

Example: a DMRPI real-source PASS may authorise the exact bounded sequence `F0-A -> F0-B -> EC1CapacityBudget -> E1 -> R1 -> RV` while still withholding candidate freeze, Development/Validation, upper-layer activation, publication and exposure. The internal stages are then automatic unless their actual PASS effects leave that envelope.

After operator PASS:

```
authorise
 -> materialise decision
 -> execute next eligible packet
 -> repair defects
 -> test
 -> QA/review
 -> auto-ratify non-reserved gate
 -> integrate
 -> close packet
 -> resolve successor
 -> continue
 -> stop only at first genuine reserved authority frontier or uncorrectable blocker
```

`OVC RUN` and `OVC CONTINUE` mandates therefore remain live across ordinary packet, review-prerequisite completion, assurance and integration boundaries unless an explicit ONLY/UNTIL/HOLD boundary says otherwise.

## 8. Failure and remediation

Correctable technical defects inside scope SHALL be repaired, retested, re-QA'd and continued without operator intervention.

Capacity problems inside the current envelope may re-plan physical execution, re-shard, re-cache, alter checkpoint cadence within bounds, optimise and retry. They may not silently change scientific population, sampling, threshold or semantics.

Missing mandatory artifact/authority is `BLOCKED`; OVC SHALL not infer it. Operator escalation occurs only when the smallest lawful resolution itself requires a reserved authority delta.

Source/semantic conflict defaults to owner/independent review or BLOCKED. Operator escalation occurs only if a governance decision remains after source truth is correctly surfaced.

## 9. Operator decision packets

An operator packet SHALL answer an authority question, not ask the operator to re-perform QA. It SHALL include current and proposed AuthorityEnvelope, exact authority delta, reserved-predicate hits, completed packets, tests, QA/reviews, warnings, unresolved items, evidence, rollback, recommendation, consequences of each disposition and the exact automatic sequence after PASS.

Allowed decisions remain `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## 10. Machine records and reason codes

Each gate instance SHALL be able to materialize a `GateAuthorityAssessment` containing programme/plan/packet identity, exact current envelope identity, proposed PASS effect, authority delta, already-delegated and net-new deltas, reserved predicate hits, reviews, blockers, hard denies, gate function, execution class, classifier version and evidence references.

Canonical automatic reasons:

- `AUTO.NO_AUTHORITY_DELTA`
- `AUTO.ALREADY_DELEGATED`
- `AUTO.MECHANICAL_CONFORMANCE`
- `AUTO.ASSURANCE_ONLY`
- `AUTO.REPAIR_WITHIN_SCOPE`
- `AUTO.OPERATIONAL_CHOICE_WITHIN_BUDGET`
- `AUTO.CLOSEOUT_ONLY`
- `AUTO.READ_ONLY_ALREADY_LAWFUL`

Canonical review reasons:

- `REVIEW.INDEPENDENT_ASSURANCE`
- `REVIEW.SOURCE_OWNER`
- `REVIEW.SEMANTIC_CONFORMANCE`
- `REVIEW.USABILITY_NON_ACTIVATING`

Canonical operator reasons are the `OPR.*` catalogue in §5.

Canonical blocker reasons include `BLOCK.MISSING_AUTHORITY`, `BLOCK.MISSING_ARTIFACT`, `BLOCK.SOURCE_CONFLICT`, `BLOCK.AUTHORITY_EFFECT_UNKNOWN`, `BLOCK.UNRESOLVED_SEMANTICS`, `BLOCK.NON_REPRODUCIBLE_EVIDENCE` and `BLOCK.CAPACITY_EXCEEDED`.

Canonical hard denies include `DENY.PROTECTED_VALIDATION`, `DENY.FORCE_PUSH`, `DENY.HISTORY_REWRITE`, `DENY.OUT_OF_SCOPE_EXECUTION` and `DENY.UNAUTHORISED_EXPOSURE`.

## 11. Existing-gate migration doctrine

Historical decisions remain immutable. Migration changes only the forward effective classification of incomplete/future gate instances.

For every incomplete gate `G`:

1. preserve the historical gate definition and source;
2. resolve exact current governing plan/version;
3. resolve current operator decisions and AuthorityEnvelope;
4. reconstruct the exact proposed PASS effect;
5. compute canonical `ΔA`;
6. run the current classifier;
7. emit a `GateMigrationRecord` recording legacy class, new class, classifier version, reason and authority delta;
8. update forward programme state only;
9. never rewrite a historical decision.

A legacy `OPERATOR_REQUIRED` label is not self-proving. It may migrate to `AUTO_RATIFIABLE` when the gate is assurance-only, or to `REVIEW_PREREQUISITE` when a real independent/human/source-owner review remains but no new authority is granted. Conversely, a legacy AUTO gate becomes `OPERATOR_REQUIRED` if its actual PASS effect contains a net-new reserved delta.

If the PASS effect cannot be reconstructed without inventing semantics, migration is `BLOCKED`.

Mixed gates retain one logical decision frontier while all mechanical prerequisites execute first.

## 12. Consolidation and already-granted authority

OVC SHOULD consolidate operator choices that belong to one genuine decision frontier. It SHALL NOT create multiple stops merely because multiple packets, technical gates or evidence producers contributed to one authority decision. Unrelated scientific, governance and exposure authority MUST NOT be hidden in one broad PASS.

For any later action `x`:

```
if x is wholly contained in effective_operator_granted_envelope:
    x is execution
else:
    classify x as a potential new authority delta
```

This is the mechanism for recursive autonomy without self-granted authority.

## 13. Migration of currently paused gates

When migration determines that a currently paused incomplete gate is `AUTO_RATIFIABLE`, and exact acceptance, QA/review, currentness, rollback and integration conditions already pass with no explicit HOLD/ONLY/UNTIL boundary, OVC SHALL record delegated PASS, integrate if eligible, close the packet and resume the persistent execution mandate without another operator command.

When migration determines `REVIEW_PREREQUISITE`, OVC SHALL not turn the missing review into an operator-authority request. It waits for or obtains the exact qualified review required by the governing contract, then continues automatically if PASS.

## 14. Ratification and migration authority

Operator decision `PASS` at `2026-08-16T00:53:00+01:00` ratifies this doctrine as the forward gate-classification constitution and explicitly authorises:

1. materialisation of this doctrine and its machine classifier/contracts;
2. deterministic forward migration of incomplete existing gates;
3. preservation of all historical gate decisions and evidence;
4. automatic continuation from reclassified gates where a live execution mandate and all prerequisites permit;
5. no relaxation of scientific, protected-role, Validation, publication, exposure, destructive or hard-deny boundaries.

Per-programme operator approval is not required merely to apply this deterministic migration rule.

## 15. Final constitutional rule

> OVC SHALL stop for the operator when the operator has something substantive to govern.

The operator governs new direction, new authority, new active state, scientific selection, protected-role progression, canonical publication, governance semantics, meaningful owner conflict, exposure, destructive action and material expansion of scope or tempo.

OVC governs implementation, tests, QA, bounded review routing, repairs, retries, performance optimisation inside the envelope, branches, PRs, exact-tree assurance, eligible integration, closeout, successor release and continuous execution.

Canonical shorthand:

```
MECHANICAL CORRECTNESS -> MACHINE
EVIDENCE / CHALLENGE   -> QA / QUALIFIED REVIEW
DIRECTION              -> OPERATOR
AUTHORITY              -> OPERATOR
TEMPO ENVELOPE         -> OPERATOR
EXECUTION WITHIN THEM  -> OVC
```

Implementation success never grants authority. Authority already granted never requires repeated human confirmation merely because implementation advanced successfully to its next deterministic state.
