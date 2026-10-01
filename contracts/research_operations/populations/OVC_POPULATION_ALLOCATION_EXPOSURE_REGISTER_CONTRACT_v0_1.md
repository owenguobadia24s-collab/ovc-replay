# OVC Population Allocation & Exposure Register Contract v0.1

Status: IMPLEMENTED / NON-AUTHORITATIVE CONTROL SURFACE
Authority effect: NONE

## Purpose
Maintain one central, append-only record of reusable market populations, research allocations and irreversible information exposure across OVC programmes. The register prevents one programme from treating a population as untouched when another programme has already consumed or disclosed it.

## Constitutional rules
1. Repository state is the control record. Drive population archives remain source owners for raw bytes; this register stores logical population identity and source-manifest references, not protected read paths.
2. `instrument × chronological partition` is the default population identity for the curated bank. 15M and native 120M are dependent clock views, not independent replications.
3. Source-bank labels `P1_DISCOVERY_DEVELOPMENT`, `P2_CONFIRMATION`, `P3_REPLICATION`, `P4_STRATEGIC_RESERVE` are descriptive construction labels only. They never grant ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT or ACTIVE_VALIDATION.
4. Discovery reuse is repeatable, but each study must disclose prior exposure and dependence.
5. Development and Validation require exact programme authority and population preflight. `UNKNOWN_REQUIRES_CENSUS` fails closed.
6. Protected Validation reservation contains no locator, credential, provider query, row selector, read path or artifact handle capable of consumption.
7. Exposure is append-only and irreversible. HUMAN, ALGORITHM and SUMMARY channels are independent.
8. One protected population may support multiple separately frozen studies in a coordinated batch, but those studies share population dependence and are not independent replications.
9. Once population evidence influences a candidate/theory/method generation, that population cannot provide untouched independent confirmation of that generation or descendants influenced by it.
10. The register reports eligibility/preflight status only. It grants no research-role activation, protected-source access, scientific promotion, publication, probability, risk, exposure, trading or execution authority.

## Objects
- `PopulationResource`: logical population and dependent clock views.
- `PopulationAllocation`: programme/study request or reservation.
- `ExposureEvent`: irreversible disclosure/consumption event.
- `PopulationEligibilityAssessment`: derived fail-closed assessment.

## Reuse semantics
- Discovery: `REUSABLE_WITH_DISCLOSURE`.
- Development: `PREFLIGHT_AND_AUTHORITY_REQUIRED`.
- Validation: `PREFLIGHT_AND_AUTHORITY_REQUIRED_UNTOUCHED_NOT_ASSUMED`.
- Post-exposure: replay/QA, robustness, historical replication and new exploration remain lawful, but untouched-confirmation claims do not.

## Rollback
Forward-supersede implementation while preserving prior snapshots and every exposure event. Exposure history is never deleted or rewritten.
