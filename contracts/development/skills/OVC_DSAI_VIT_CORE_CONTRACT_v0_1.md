# OVC DSAI v0.3 VIT Core Contract v0.1

Authority: inactive implementation only. Physical main remains the sole court record. This contract grants no live VIT materialisation authority.

## Normative identities
- `PacketIntegrationPayload` is content-addressed from packet mutation, exact authority manifest, exact dependency frontier and prepared completion transition. Branch, PR, worker and commit metadata are provenance only.
- `ProspectiveTreeState` identity is exact Git tree object identity under `TREE_IDENTITY_PROFILE_git-tree-v1`.
- `VirtualIntegrationGeneration` binds predecessor tree, PIP, train placement, authority/dependency frontiers and resulting tree.
- Equal trees may have distinct generation lineage; PIP identity survives reordering.

## Closed objects
`ContinuousExecutionMandate`, `DevelopmentLane`, `PacketPredecessorRequirement`, `PacketIntegrationPayload`, `IntegrationAuthorityManifest`, `DependencyFrontier`, `VirtualIntegrationLedger`, `VirtualIntegrationGeneration`, `ProspectiveTreeState`, `IntegrationTrainGeneration`, `IntegrationTicket`, `CompositionReceipt`, `InvalidationGraph`, `PhysicalMainAnchor`, `PhysicalMaterialisationTransaction`, `PhysicalIntegrationLease`, `PhysicalMaterialisationReceipt`, `PacketCompletionReceipt`, `AuthorizedExternalMainAdvanceReceipt`, `VITOperationalBudget`, `StateDrainageManifest`, and `VITRebuildManifest`.

## Closed predecessor requirements
`PHYSICAL_MATERIALISATION_REQUIRED`, `QUALIFIED_VIT_GENERATION_REQUIRED`, `PAYLOAD_OUTPUT_REQUIRED`, `EXECUTION_COMPLETION_REQUIRED`, `ORDER_ONLY`, `NONE`.

## Closed conflict classes
`COMMUTATIVE`, `ORDER_SENSITIVE`, `SERIAL_REQUIRED`, `MUTUALLY_EXCLUSIVE`, `UNKNOWN`. Unknown is fail-closed and is never treated as commutative.

## Authority firewall
`AUTO_EXECUTABLE` with `authority_delta=NONE` may enter prospective computation only. `OPERATOR_REQUIRED` produces `WAITING_OPERATOR_AUTHORITY`. `HARD_DENY` denies. Queue age, VIT order, technical PASS and availability never create authority.

## Tree equality
Physical/prospective equality is exact Git tree object ID. Commit SHA, message, timestamps, author and committer metadata cannot create equality or inequality. Tree mismatch emits `POST_WRITE_TREE_MISMATCH` and may never be accepted as completion.

## Canonical serialization
Identity-bearing records use the existing OVC canonical JSON/SHA-256 implementation in `ovc.development.identity`. Host paths, runtime timestamps and presentation fields are excluded unless a record contract explicitly declares them identity-bearing.

## Catalogue bindings
The logical artefact catalogue identifiers are: `CONTINUOUS_EXECUTION_MANDATE_CONTRACT_v0_1`, `DEVELOPMENT_LANE_CONTRACT_v0_1`, `PACKET_PREDECESSOR_REQUIREMENT_REGISTRY_v0_1`, `PACKET_INTEGRATION_PAYLOAD_SCHEMA_v0_1`, `INTEGRATION_AUTHORITY_MANIFEST_SCHEMA_v0_1`, `DEPENDENCY_FRONTIER_SCHEMA_v0_1`, `VIT_LEDGER_CONTRACT_v0_1`, `VIT_GENERATION_SCHEMA_v0_1`, `PROSPECTIVE_TREE_STATE_SCHEMA_v0_1`, `INTEGRATION_TRAIN_GENERATION_SCHEMA_v0_1`, `INTEGRATION_TICKET_SCHEMA_v0_1`, `COMPOSITION_RECEIPT_SCHEMA_v0_1`, `INVALIDATION_GRAPH_SCHEMA_v0_1`, `PHYSICAL_MAIN_ANCHOR_SCHEMA_v0_1`, `PHYSICAL_MATERIALISATION_TRANSACTION_SCHEMA_v0_1`, `PHYSICAL_INTEGRATION_LEASE_CONTRACT_v0_1`, `PHYSICAL_MATERIALISATION_RECEIPT_SCHEMA_v0_1`, `PACKET_COMPLETION_RECEIPT_SCHEMA_v0_1`, `AUTHORIZED_MAIN_WRITER_REGISTRY_v0_1`, `AUTHORIZED_EXTERNAL_MAIN_ADVANCE_RECEIPT_SCHEMA_v0_1`, `VIT_OPERATIONAL_BUDGET_SCHEMA_v0_1`, `STATE_DRAINAGE_MANIFEST_SCHEMA_v0_1`, `VIT_REBUILD_MANIFEST_SCHEMA_v0_1`, `TREE_IDENTITY_PROFILE_git-tree-v1`, `INTEGRATION_APPLY_PROFILE_REGISTRY_v0_1`, `VIT_REASON_CODE_REGISTRY_v0_1`.
