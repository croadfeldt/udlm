# UDLM file index — what each document owns

**Purpose.** One home per concept. This index says, for every normative document, *what it is* and *what it canonically owns* — so before you write a rule, vocabulary, or wire-shape, you can find the file that already owns it and **reference it** rather than restate it. This is the human-readable companion to the single-source rule (`registry/SPEC-DESIGN-REQUIREMENTS.md` §33) and its check (`tests/check_single_source.py`).

**How to use it.** Look up the concept you're about to write. If a file below already *owns* it, put your rule there (or reference its ID). If nothing owns it, the file whose purpose is the closest fit is the home — add it there and note the new ownership here. Never define the same rule in two files; cite the owning file's ID with a one-line gist — the reference carries its own gist (e.g. `ADR-008 — the UDLM/DCM boundary test`), never a bare pointer.

Rule-ID families (`INF-*`, `ENT-*`, `DPO-*`, …) each belong to exactly one file — the "Owns" line names them.

---

## Root

- **`README.md`** — project entry point and orientation. *Owns:* nothing normative; summarizes and links.
- **`CONFORMANCE.md`** — what wire-level conformance certifies (and does not), the declaration shape, levels, and the wire-compatibility checklist. *Owns:* conformance levels, the `.well-known` declaration, the required-contracts list (§5), the wire-compat checklist (§6).
- **`GLOSSARY.md`** — human-readable term definitions. *Owns:* short prose glosses only; the machine taxonomy lives in `registry/resource-types/taxonomy-term.json`.

## `foundations/` — the core model everything else builds on

- **`foundations.md`** — the three abstractions (Data · Provider · Policy). *Owns:* the abstraction triad.
- **`data-model-core.md`** — *normative* core. *Owns:* the `lifecycle_state` five-value enum, the drift-severity enum, the `kind`+`relation` relationship model (§4), and the `[D1]–[D7]` core rules — including that operational/health are `status.conditions` and Process run dynamics are `execution_state`.
- **`four-states.md`** — the canonical definitions of Intent / Requested / Realized / Discovered and their immutability. *Owns:* the four-state semantics (the enum values themselves are in data-model-core §3).
- **`entity-types.md`** — the entity families (Resource, Process) and the derived Atomic/Composite shape (`has_constituents`), and their data models. *Owns:* the entity-type taxonomy, `ENT-*` entity-type invariants.
- **`entity-type-families.md`** — the logical family grouping (Resource family, Knowledge family). *Owns:* family membership.
- **`ownership-sharing-allocation.md`** — the ownership model. *Owns:* the `ownership_model` vocabulary (`whole_allocation | allocation | shareable`) and allocation semantics.
- **`layering-and-versioning.md`** — data layers and the assembly process. *Owns:* the layer model and the artifact status lifecycle (`active → deprecated → retired`) + transition rules.
- **`layering-and-versioning-annex.md`** — non-normative worked detail for the above.
- **`context-and-purpose.md`** — orientation/summary; defers to the canonical homes.
- **`examples.md`** — non-normative worked examples.

## `contracts/` — the wire contracts between DCM and providers/peers

- **`provider-contract.md`** — the unified provider base contract + capability extensions (§8). *Owns:* the base registration/health/lifecycle floor, `PRV-*`, the reserve/commit two-phase realize.
- **`capability-discovery.md`** — the unified provider/capability model. *Owns:* the verb×domain capability model, capability categories, and the default-deny admission formula (`declared ∩ admitted ∩ registry-enabled ∩ matrix-permitted`).
- **`policy-contract.md`** — the unified policy contract. *Owns:* policy evaluation surface, `POL-*`.
- **`data-store-contracts.md`** — enforcement contracts for the four data domains + audit. *Owns:* the Realized/Audit store domain invariants.
- **`storage-providers.md`** — the storage capability extension. *Owns:* store sub-profiles (GitOps/snapshot/event/search/audit) and `STO-*` — *not* provider types.
- **`information-providers.md`** — the `serve_data` capability. *Owns:* information-provider registration.
- **`information-providers-advanced.md`** — confidence, authority, schema versioning for information providers. *Owns:* `authority_level` not-self-declared and the IP `INF-*` rules (`INF-*` is now solely the information-provider family — data-contracts' former `INF` family renumbered to `DSC-*`).
- **`error-model.md`** — *Owns:* the error envelope (RFC 9457).
- **`event-catalog.md`** — *Owns:* the event catalog and delivery semantics (the wire event shapes).
- **`identifier-scheme.md`** — *Owns:* the UUID / handle / reference identity contract.
- **`time-and-clock.md`** — *Owns:* the timestamp format and clock model.
- **`schema-sharing.md`** — *Owns:* the schema-sharing/extension protocol.
- **`rate-limit-and-backpressure.md`** — *Owns:* rate-limit + backpressure semantics.
- **`retry-semantics.md`** — *Owns:* retry/idempotency semantics.
- **`provider-callback-auth.md`** — *Owns:* provider callback authentication.
- **`data-roles.md`** (PROPOSED) — *Owns:* the `role:` data-role vocabulary that crosses the dispatch boundary.
- **`cost-metering-linkage.md`** (PROPOSED) — *Owns:* the cost-engine linkage contract.

## `design-principles/` — see `design-principles/README.md` for the in-directory index

- **`core-tenets.md`** — hard boundaries. *Owns:* `T1–T6`.
- **`design-priorities.md`** — ranked priorities + the profile and authority-tier *vocabularies*. *Owns:* `Priority 1–4`, `DPO-*`, the profile name vocabulary (nature of a profile defers to ADR-007).
- **`cross-cutting-requirements.md`** — always-on obligations. *Owns:* `P0–P4`.
- **`adopted-standards.md`** — how external standards enter (the *Adopt* disposition). *Owns:* the absorb/embed/adopt test + adoption constructs.
- **`data-contracts.md`** — the data-contract principle + the four persistent domains. *Owns:* `DSC-001–DSC-007` (persistence; the former data-contracts `INF-*` family, renumbered).

## `governance/`

- **`credentials.md`** — *Owns:* the closed `credential_types` vocabulary (§2), the `credential_capability` declaration (§9), and the credential record / scope wire-shape (§5) — the single home for anything credential-shaped.
- **`auth-providers.md`** — the auth capability. *Owns:* auth provider registration + authentication-mode taxonomy (credential vocabulary defers to `credentials.md`).
- **`authority-tier-model.md`** — *Owns:* the ordered authority-tier vocabulary and the `decision_gravity` mapping.
- **`accreditation-and-authorization-matrix.md`** — *Owns:* accreditation types, the data-authorization matrix, and zero-trust posture levels.
- **`governance-matrix.md`** — *Owns:* the (boolean) Governance Matrix evaluated at every boundary crossing.
- **`federated-contribution-model.md`** — *Owns:* the federated-contribution (shadow-mode) model.
- **`registry-governance.md`** — *Owns:* registry governance + sunset policy (`REG-DP-*`); versioning defers to `registry/VERSIONING.md`.

## `entities/`

- **`resource-service-entities.md`** — resource/service entity lifecycle + Process entities. *Owns:* `RSE-*`; the operational-phase overlay (coarse lifecycle defers to data-model-core §3).
- **`composite-service-model.md`** — *Owns:* composite composition + compensation semantics.
- **`entity-relationships.md`** — the universal relationship *structure*. Note: the relationship type model is **superseded by data-model-core §4**; this file retains the inverse vocabulary + `XTA-*` cross-tree rules.
- **`service-dependencies.md`** — *Owns:* the dependency graph, rehydration ordering, `DEP-*`.
- **`resource-grouping.md`** — *Owns:* grouping, tenant boundaries, the DCMGroup / `GRP-*` model.
- **`resource-type-hierarchy.md`** — *Owns:* the resource-type hierarchy + service-catalog structure.
- **`knowledge-family.md`** — *Owns:* the Knowledge entity family (Capability, TaxonomyTerm) — anchored by DAV.

## `registry/` — the machine-checked spec surface + policy

- **`VERSIONING.md`** — *Owns:* the two-axis (SPEC / ENTITY) versioning + compatibility policy. The single versioning home.
- **`naming-conventions.md`** — *Owns:* casing (`snake_case`), `Category.Type` naming, file naming, the name-to-a-standard rule.
- **`common-elements.md`** — *Owns:* canonical shared shapes reused across types (`REL-*` shared elements, common patterns).
- **`SPEC-DESIGN-REQUIREMENTS.md`** — *Owns:* the resource-type-spec rubric (MUST/SHOULD), including §33 the single-source rule.
- **`standards-adoption-register.md`** — *Owns:* the per-standard adoption decision + license verdict (`ADOPT-001`). The single home for license verdicts.
- **`resource-type-data-sources.md`** — per-type "what it adopts by reference" mapping (design input; license verdicts defer to the register).
- **`REALIZED-ENTITY.md`** — the realized-entity instance schema, in prose.
- **`UDLM-1.0-SCOPE.md`** — the 1.0 scope + exit criteria.
- **`README.md`** — registry overview.

## `observability/`

- **`audit-provenance-observability.md`** — *Owns:* the audit/provenance/observability model, `AUD-*` / `OBS-*`.
- **`universal-audit.md`** — *Owns:* the universal audit record model.
- **`universal-groups.md`** — *Owns:* the universal group model (`GRP-*` where it extends grouping).

## `lifecycle/`

- **`ingestion-model.md`** — *Owns:* the ingestion model.
- **`operational-models.md`** — *Owns:* operational models, `OPS-*`.
- **`request-dependency-graph.md`** — *Owns:* the consumer request dependency graph + binding fields.
- **`scheduled-requests.md`** — *Owns:* scheduled/deferred requests.
- **`subscription-lifecycle.md`** — *Owns:* subscription lifecycle.

## `docs/` and `docs/adr/`

- **`docs/adr/`** — Architecture Decision Records. A ratified ADR is the authority for the decision it records; spec prose conforms to it, never contradicts it (e.g. ADR-007 owns "profiles are composed sets, not levels"). Its README also indexes the **instance-backed `ADR-<FAMILY>-NNN` namespace** (`ADR-PROV/RBAC/COST/AEP-*`) — DecisionRecord JSON in `registry/instances/`, resolvable only through that index.
- **`docs/`** — narrative/vision/design notes (non-normative unless they state otherwise).
- **`docs/internal/`** — working notes (gitignored); not part of the published spec.

---

*Keep this current: when a document changes what it owns — a new rule-ID family, a moved vocabulary, a rename — update its line here in the same change.*
