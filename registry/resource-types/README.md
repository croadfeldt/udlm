# resource-types/ — directory structure by class

Type specs are grouped into one subdirectory per class. The grouping rule is deterministic —
a spec's directory is derived from the document, never chosen:

1. **Dotted `resource_type`** (`Compute.VirtualMachine`, `Network.VLAN`, …): the directory is
   the **lowercased first segment** — `compute/`, `network/`, `storage/`, `hardware/`,
   `platform/`, `security/`, `identity/`, `data/`, `software/`, `facility/`,
   `observability/`, `automation/`, `access/`.
2. **Single-word `resource_type`** (`SoftwareImage`, `Vulnerability`, `Topology`, …): the
   directory is the **lowercased `family`** field of the document — `knowledge/`,
   `resource/` (whatever families exist; ADR-027 defines the family tier).

Filenames are unchanged by the grouping — only directories were added. Directory location is
**navigation, not identity**: a type's identity is `resource_type` (the handle) plus its
frozen `uuid`, and a revision is a published (version, digest) pair (`VERSIONING.md`
§ "Identity, version, digest"). Tooling discovers specs
recursively (`registry/tools/validate.py`, `fuzz_type_specs.py`, `generate_type_catalog.py`,
`model_health.py`; `tests/`), so a new class directory needs no tool change.

Any path rename ships with an old → new map in [`../renames.yaml`](../renames.yaml) — the
rename-map discipline; base-ref-diffing gates (`tests/ci_compat_gate.py`,
`tests/check_identity_integrity.py`) consult it so a renamed file is compared as the same entity.
