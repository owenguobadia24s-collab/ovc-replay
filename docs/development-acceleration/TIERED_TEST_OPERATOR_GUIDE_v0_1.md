# OVC Tiered Test Selection — Operator Guide v0.1

## Purpose

The selector provides early feedback from a frozen changed-file inventory while preserving complete stable-head assurance. It does not decide whether a pull request may merge.

## Select from explicit paths

```powershell
$env:PYTHONPATH = "src"
python scripts/development/ovc_test_select.py `
  --registry registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_1.json `
  --changed-path src/ovc/development/test_selection.py `
  --changed-path tests/development/test_test_selection.py
```

## Select from an inventory file

```powershell
python scripts/development/ovc_test_select.py `
  --registry registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_1.json `
  --changed-paths-file changed-paths.txt `
  --output test-selection-manifest.json
```

The output is deterministic compact JSON. Unknown paths select `FINAL_HEAD`. An empty inventory or ambiguous highest-priority mapping blocks.

## Gate replay

```powershell
python scripts/development/ovc_test_select.py `
  --registry registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_1.json `
  --changed-paths-file changed-paths.txt `
  --stage GATE_REPLAY `
  --gate-id DA-G3 `
  --gate-command "PYTHONPATH=src python scripts/development/validate_da_g3.py"
```

Gate replay is additional evidence. It never substitutes for the complete repository suite on a stable PR head or after a base change.

## Exit codes

- `0`: valid PASS manifest;
- `1`: valid selection that BLOCKED because of ambiguity;
- `2`: invalid registry, unsafe path, empty inventory or invalid request.

## Adoption boundary

The `OVC tiered test selection shadow` workflow is restricted to Development Acceleration paths. Broad repository-default adoption and retirement of duplicated mechanics remain denied until operator-required DA-G6.

## Rollback

Stop invoking the selector or revert the bounded DA-WP3 merge. Preserve generated manifests. Existing workflows and final-head assurance remain authoritative.
