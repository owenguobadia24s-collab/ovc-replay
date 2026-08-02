# MTA required-check compatibility record v0.1

## Purpose

This compact court record exists because the repository currently requires the path-bounded `OVC tiered test selection shadow` check before merge, while its pull-request path filter does not yet include Market Translation Audit paths.

The MTA-G0 pull request therefore includes this documentation-only path so the existing required shadow selector runs without modifying the Development Acceleration workflow, test-profile registry, authority profile, or broad workflow-adoption boundary.

## Scope

- programme requiring assurance: `OVC-MTA-v0.2`
- gate: `MTA-G0`
- pull request: `210`
- MTA operator decision: `MTA-G0.OPERATOR.PASS.20260802T145100Z`
- expected selector treatment: unknown changed MTA paths escalate to `FINAL_HEAD`
- authority delta: `NONE_REQUIRED_CHECK_COMPATIBILITY_RECORD_ONLY`

## Retained boundaries

This record does not:

- activate broad default-workflow adoption;
- change the tiered-test workflow or registry;
- grant repository-bot authority;
- alter market, selector, release, Validation, C2E, C2.5, C3, probability, risk, exposure or execution authority;
- substitute the tiered shadow check for MTA-G0 or generic final-head assurance.

## Removal or supersession

A later Development Acceleration gate may lawfully extend the workflow path filter to MTA paths. Until then, this record is preserved as the explicit reason the existing required check was triggered; it must not be silently deleted or treated as broad workflow adoption.
