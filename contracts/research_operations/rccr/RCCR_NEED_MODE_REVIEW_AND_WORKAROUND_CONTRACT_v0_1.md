# RCCR Need, Mode, Human Review and Workaround Contract v0.1

Programme: `OVC-RCCR-CONFORMANCE-v0.1`  
Packet: `RCCRI-WP5`  
Authority effect: `NONE`

## Capability-need semantics

A `CapabilityNeedAssessment` is eligible only after `CounterfactualSufficiencyReview` admits a real `INFORMATION_GAP`. One record names one exact candidate capability, owner and owner-contract reference. Existence, demand frequency, implementation cost, sunk cost and architectural convenience have zero need-status authority.

`NEED_SUPPORTED` requires all of: a real information gap after smaller explanations are exhausted; exact owner fit; minimality; QA `PASS`; and semantic-owner and/or shadow-closure evidence. `NEED_CONTRADICTED` is emitted when lawful counterevidence or closure testing shows the capability does not close the gap or a smaller route suffices. Reviewer conflict is `UNRESOLVED`; no majority vote is permitted. Every result retains `authority_requested=NONE` and `authority_effect=NONE`.

## Mode and influence firewall

The firewall implements `PATH1_PRE_FREEZE`, `PATH2_PRE_FREEZE`, `CROSS_MODE_POST_FREEZE`, `OPERATOR_RESTRICTED` and `GENERAL_RESEARCH` visibility classes. Candidate-defining Path-2 material is denied to Path-1 pre-freeze; emergent Path-1 forms are denied to Path-2 pre-freeze without an exposure record. Cross-mode use requires the exact freeze/release condition and resolved exposure. Operator inspection does not become decision-bearing use unless material influence is recorded. Independence defaults to `UNKNOWN`; absence of a contamination record never implies `INDEPENDENT`.

## Human review

Eligible roles are Requirement Reviewer, Owner-Fit Reviewer, Minimality Reviewer, Mode-Firewall Reviewer and Pilot-Exit Reviewer. Each queued/completed review preserves identity, role, subject, reviewer, input references, timing, conflict/common-ancestry disclosure, decision, rationale, resolution authority, counterevidence/reopen evidence and first-valid time. Conflicting eligible judgments remain `UNRESOLVED` and escalate; repeated votes cannot manufacture scientific truth.

Review telemetry is denominator-complete and descriptive only: route/completion/pending counts, queue age, median/tail review latency, reopen count/rate, unresolved/conflict count, operator escalation count and per-role latency denominators. These measurements may drive workflow redesign or the later `RCCRHumanReviewBudget`; they cannot alter a scientific gap or need state.

## Off-register workaround pressure

`OffRegisterWorkaroundRecord` is an operational, non-canonical bounded record available before any Console-facing RCCR work. It records attempted route, blocked cause, workaround class, burden, resolution, escalation and first-valid time. If external rationale would become decision-bearing, an exact provenance reference is mandatory before use. Workaround counts/rates are operational diagnostics only and never targets or rankings.

## Fail-closed conditions

Unknown visibility, review role, independence state, owner-fit state or minimality state fails closed. A need object with more than one candidate capability is invalid. Missing falsifiers, owner route or shadow route is invalid. No WP5 output activates a capability, changes source/owner authority, consumes real-source EC1 or Validation, publishes evidence, or grants probability/risk/exposure/trading/execution/agent-write authority.
