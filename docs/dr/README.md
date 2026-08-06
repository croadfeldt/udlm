# UDLM Decision Records (project & process)

Decisions about **how we build** — conventions adopted, where prose lives, process rulings —
as distinct from **architecture** decisions, which are ADRs in [`../adr/`](../adr/) and which a
peer implementing UDLM must honor. Same prose shape (Background on-ramp → Context → Decision →
Consequences); different subject. Both tiers are indexed in the
[decisions register](../adr/README.md).

| DR | Decides | Status |
|---|---|---|
| [DR-AEP-001](DR-AEP-001-adopt-aep-conventions.md) | Adopt the AEP conventions — RFC 9457 via AEP-193 for the error envelope, resource-oriented design for the API surface, the Spectral linter for the specs | Proposed |
| [DR-UDLM-DCM-001](DR-UDLM-DCM-001-runtime-prose-lives-in-dcm.md) | UDLM carries the data model; runtime-architecture prose (assembly, evaluation mechanics, storage, pipelines) lives in DCM's documentation | Proposed |
