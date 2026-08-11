# RCN-RN-WP3E — Autonomous Visual Convergence

**Addendum ID:** `OVC-RCN-RN-WP3E-AUTONOMOUS-VISUAL-CONVERGENCE-ADDENDUM-0.1`  
**Parent plan:** `OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.3-RATIFIED`  
**Programme:** `OVC-RC-VNEXT-GREENFIELD-v0.1`  
**Packet:** `RCN-RN-WP3E`  
**Status:** OPERATOR APPROVED / READY FOR REPOSITORY MATERIALISATION  
**Prepared / approved:** 11 August 2026  
**Baseline:** `main@8fa5fd8c17ae972867f857e631048a3766218b47`  
**Authority effect:** NONE; fixture-only local read-only remains controlling.

## 1. Decision

Insert one bounded remediation packet between completed `RCN-RN-WP3D` and the next `RCN-RN-G3V`. The closed-unmerged PR #585 candidate is rejected/superseded as a visual acceptance candidate. `G3V` is deferred until autonomous convergence completes. No `WP4` or `G4` work is admitted while WP3E is open.

## 2. Governing visual authority

WP3E is governed by `design/research_console/visual_target/OVC_Research_Console_Visual_Target_and_Convergence_Contract_v1_0.md` and canonical `VT-REF-01..04`. The contract is binding for composition, density, hierarchy, panel discipline, domain identity and analytical-instrument quality. The prototypes are not scientific or write authority.

## 3. Scope

WP3E may modify fixture-only Research Console frontend implementation, local visual-test harnesses, screenshot tooling, styles, layout primitives and component presentation needed to converge on the canonical reference family. It may refactor visual component structure where semantics and generated/read-model contracts remain unchanged.

WP3E MUST NOT:

- bind real sources or begin `WP4/G4`;
- change scientific/source ownership or infer new market meaning;
- activate selectors, families, ObjectPacks, C2.5 vocabularies or C3 semantics;
- consume Validation or create probability/risk/exposure/trading/execution authority;
- introduce write-capable console behaviour;
- weaken FVT, missingness, denominators, QA, evidence identity or fail-honest degradation.

## 4. Autonomous convergence loop

The implementation agent SHALL execute this loop without operator interruption for ordinary refinement:

`inspect target → render current exact head → compare → rank discrepancies → implement coherent correction batch → test → rerender → update discrepancy ledger → repeat`

A pass is an internal remediation cycle, not a gate. “Improved” is not completion.

## 5. Stop conditions

The agent may stop before final acceptance only for one of these typed conditions:

1. `CONTRACT_CONFLICT` — canonical references or binding requirements cannot be reconciled without operator interpretation.
2. `AUTHORITY_CONFLICT` — a required correction would cross the current read-only/scientific boundary.
3. `TECHNICAL_IMPOSSIBILITY` — a platform/toolchain constraint prevents a blocking criterion and evidence proves the constraint.
4. `CURRENT_MAIN_CONFLICT` — concurrent main movement materially changes the implementation surface and requires re-preflight.
5. `FINAL_G3V_READY` — every blocking `VC-01..VC-18` criterion passes on exact head with required two-pass stability.

Ordinary CSS, spacing, component geometry, typography, density, panel balance, responsive behaviour and visual-instrument refinements are **not** escalation reasons.

## 6. Required evidence

Maintain a machine-readable or Markdown discrepancy ledger for each pass containing:

- exact commit SHA;
- viewport;
- reference(s) compared;
- top ranked discrepancies;
- correction batch;
- semantic/component test result;
- render evidence path/hash;
- `VC-01..VC-18` status;
- next highest-impact discrepancy.

The final packet additionally requires 1920×1080, 1440×810 and 1280×720 exact-head renders, semantic/read-only assurance, full repository CI and two consecutive passes with no blocking regression.

## 7. Gate consequence

WP3E completion does not itself PASS G3V. It may only transition the programme to `G3V_READY_FOR_FINAL_OPERATOR_ACCEPTANCE`. The operator then sees one final candidate. `PASS` at that later gate may admit WP4 preparation under the parent plan; real-source exposure remains separately reserved to `RCN-RN-G4`.

## 8. Codex execution binding

Codex must load the repository root `AGENTS.md` and `.agents/skills/ovc-visual-convergence/SKILL.md`. The Codex-host skill is an implementation workflow surface. It is **not** a DSA TRUSTED Skill, does not inherit DSA runtime authority, and may later be registered/qualified by the separately governed Development Skills Architecture programme.

## 9. Rollback

Close or supersede the WP3E branch/PR without merging. Preserve all render/discrepancy evidence. `main@8fa5fd8c17ae972867f857e631048a3766218b47` remains the fixture-only implementation baseline and G3V stays deferred. No real-source authority is affected.
