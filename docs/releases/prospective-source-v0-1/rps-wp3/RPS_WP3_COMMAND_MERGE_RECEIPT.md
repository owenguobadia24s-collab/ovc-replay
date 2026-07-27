# RPS-WP3 — Command Merge Receipt

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP3`
- Pull request: `#107`
- Final command-ready head: `48dee2cbeb7b365853b5ae4616ad0d8c52214b4e`
- Dedicated workflow: `30291002463`
- Dedicated job: `90060487550`
- Canonical workflow: `30291002498`
- Canonical job: `90060487801`
- Squash merge: `4ccda083ddbe099056da4d1ce068ab63ba816c9a`
- QA: `PASS_COMMAND_READY`
- Merged on: `2026-07-27`

## Result

The exact operator-local RPS-WP3 derived compute command is present on `main`. RPS-WP3 remains `RUNNING` because no real external compute run or source-binding candidate has been reproduced by GitHub.

## Continuation

Pull `main`, run `scripts/run_rps_wp3_compute.ps1` with `preflight` and `execute`, then provide the five compact compute files for RPS-G3 evaluation.

## Authority

Provider access, source mutation, release or selector mutation, R2 publication, Validation consumption, LIVE_PROSPECTIVE append, ACTIVE_RESEARCH_TRIAGE and write authority remain denied.

## Rollback

Revert the RPS-WP3 command merge and this receipt while preserving the accepted RPS-G2 source, all source/compute quarantines and compact evidence. No external deletion or relabelling is authorised.
