# OVC Development Skills Security Runtime Contract v0.1

Programme `OVC-DSAI-v0.1` — packet `DSAI-WP5 / DSAI-G5`.

Security decisions are deny-by-default and are the intersection of capability, semantic action, reachable adapter, path scope, semantic ownership, recorded authority and runtime profile. Code existence never grants reachability or authority.

## ExecutionSecurityEnvelope
An envelope names exact Skill/capability identity, allowed semantic actions, read/write prefixes, semantic owners, logical credential IDs, network allowlist, filesystem-zone profile and whether a separately authorised write capability is active. WP5 registry profiles keep writes inactive.

## HARD_DENY
`FORCE_PUSH`, `HISTORY_REWRITE`, `MERGE`, `SECRET_ACCESS`, `RAW_CREDENTIAL_READ`, `VALIDATION_DISCOVERY`, `VALIDATION_READ`, selector/scientific/publication/exposure/execution actions cannot be enabled by a Skill request.

## Credentials
Skill code receives logical credential handles only. Raw secret material is prohibited from ToolRequest, SecurityDecisionRecord and receipts.

## Isolation
Zone 0 = immutable governing sources; Zone 1 = repository read surface; Zone 2 = bounded packet write-set (inactive in WP5); Zone 3 = external artifact staging under explicit profile; Zone 4 = protected/denied resources including Validation and credential stores. Network is denied unless explicitly allowlisted. DMRP Path-1 and Path-2 sandboxes are isolated by profile identity and may not infer cross-path access.

## Tool Broker
The WP5 Tool Broker has narrow local Git-read, filesystem-read and test adapters. It is inactive by default; test mode proves decision routing without executing side effects. No ORCH write authority is activated.

## Containment
S3/S4 security incidents synchronously deny privileged actions and may terminate the affected sandbox before notification/review completes.

## Rollback
Disable Tool Broker registrations and security adapters, return Skills to shadow/manual path, preserve incident/evaluation evidence.
