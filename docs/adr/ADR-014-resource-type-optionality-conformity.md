# UDLM ADR-014: Resource-type data — optionality with conformity (transport, not policy)

**Status:** Accepted (maintainer decision, 2026-07-15)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-008 (UDLM/DCM boundary); DCM ADR-023 (provider naturalization); ADR-013 (hardware scope — the same "transport, not SoR" spirit); reviewer feedback on `dcm-project/udlm` #40 (Noam `NoamNakash`, Ondra `machacekondra`).

## Context

Review of the resource-type schemas (#40) surfaced a consistent over-reach: the data was encoding **provider/organization policy** rather than portable contract. Two examples:

- **Sizing was raw-only.** `resources: {cpu, memory}` couldn't express a resource that ships **sized-by-class** (managed databases, VMs, node pools — `small|medium|large`, or a provider instance class like `db.r5.large`).
- **Relationship requirement was baked into the type.** Whether a `Storage.Volume` (or any dependency) is *required* varies by provider and by organization — one provider mandates it, another treats it optional — yet a type spec that fixes the cardinality decides that for everyone.

The underlying question: **what does a resource type's *data* own, and what does it delegate?**

## Decision

A resource type's data provides the **data transport plus a conformity contract** — **not** the provider's or organization's policy choices, and not the concrete definitions.

### 1. Optionality is delegated to the provider and the organization

**What is *required* vs *optional* — a relationship, a field — is the provider's and the organization's to own.** One provider may require a `Storage.Volume`; another may treat it as optional; a given organization may mandate it by policy. That is *their* choice, not the type's. So:

- A type declares relationships/fields **permissively** — optional cardinality (`0..1` / `0..n`) where the requirement is provider- or org-variable. The `cardinality` vocabulary already carries this (`0..1|1..1|0..n|1..n`); `1..x` is reserved for a requirement that is **universal** to the type, not merely common.
- The **actual** requirement is stated by the **provider** (its capability declaration + naturalization) and/or **organization policy**, not by the type spec. UDLM does not bake a provider's or org's requirement into the shared type.

### 2. Conformity is retained by UDLM

Delegating optionality does **not** make the data a free-for-all. **UDLM provides enough conformity that intent is comparable and portable across adjacent compatible providers.** The *vocabulary and shape* are shared contracts:

- A size class (`instance_size`) is an **ordered, comparable vocabulary**: `medium` must mean something *comparable* across compatible providers, so a workload can move between them without re-sizing (`common-elements §2.2`).
- A relationship `kind`/`target` is a shared, adopted vocabulary (TOSCA-aligned) — an edge means the same thing everywhere.

This is the portability guarantee UDLM exists for: a consumer authors comparable intent once and it moves.

### 3. The provider owns the concrete definition

The **exact mapping** — `medium` → 4 vCPU / 32 GB / `db.r5.large`, or the precise requirement gate — is the provider's, resolved at **naturalization** (DCM ADR-023). UDLM carries the comparable *shape*; the provider fills the concrete *definition*.

**Comparing the abstract to the precise.** The shared vocabulary gives *ordinal* comparability (`medium < large`), but comparing an abstract size against a **raw** requirement (or one provider's class against another's) needs the raw resolution — which only the provider knows. So the provider **declares its class → raw catalog** in its capability (`provider-contract.md §8.1a` `instance_size_catalog`); DCM resolves a size class to raw through that catalog and applies the same capacity-sufficient test as a raw request. It is **declared, not live-queried** — placement scores many providers at once, so a per-request round-trip per provider is prohibitive. Vocabulary → portability (UDLM); catalog → precision (provider); resolution/comparison → placement (DCM).

### The rule of thumb

> **Transport + conformity → UDLM. Requirement choice + concrete mapping → provider/org.**
> If it's a portable, comparable shape, it belongs in the type. If it's "is this required here?" or "what exactly does this size mean?", it belongs to the provider (naturalization) or organization (policy).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the transport (fields, relationships, cardinality) + the conformity contract (comparable size-class vocabulary, shared relationship vocabulary). Permissive by default where requirement varies.
- **Policy (DCM/org):** organizational requirement — "in this org, a database MUST have a backup volume" — is a policy over the permissive type, not a type change.
- **Provider:** declares its actual requirements and owns the concrete `instance_size`→resources mapping at naturalization.

## Options considered
- **Prescribe requirement + concrete sizing in the type** — rejected: it decides provider/org policy for everyone and breaks the moment two providers disagree (the #40 finding).
- **Free-form per-provider data (no conformity)** — rejected: intent stops being portable; the same request means different things per provider, defeating UDLM's reason to exist.
- **Transport + conformity in the type; requirement + concrete mapping delegated to provider/org** — **chosen.**

## Consequences
- Sizing gains a shared, comparable `instance_size` (common-elements §2.2); types adopt it alongside raw resources.
- Relationships whose requirement is provider-/org-variable declare optional cardinality; `1..x` means *universally* required only.
- Providers declare actual requirements + concrete mappings; organizations express additional requirements as policy.
- **A catalog sweep** applies this to the existing resource types (which need `instance_size`; which relationships should be optional) — tracked separately.
- Same family as ADR-013: UDLM carries the portable contract, not the provider's implementation or the org's policy.
