# UDLM ADR-024: Filling provider-required inputs — layers stage data, policies refine and validate

**Status:** Proposed (2026-07-16)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-016 (provider-specific config lives off the portable type, stored as `provider_extensions` — deprecated, subsumed by ADR-038's Provider-Class `SharedDataElement`, retiring per #202);
ADR-011 (validate-and-reserve — the completeness gate); `foundations/layering-and-versioning.md` §1a (layers
are data, policies are logic), §5 (precedence), Step 7 (post-placement policy); `contracts/policy-contract.md`
§12 (transformation / enrichment). **Flow:** `docs/flows/request-realization.md`.

## Context

**This ADR validates and documents the original layers/policies model; it introduces no new mechanism.** The
split — *layers are data, policies are logic* (`layering-and-versioning.md` §1a) — already answers how a
provider-required field gets filled. The namespace question surfaced the need to state that answer plainly
and to confirm no new primitive is required. Recording it here settles the question and gives the team one
place to point to.

A portable request is incomplete on purpose: the abstract `Compute.VirtualMachine` carries `guest_os`, size,
disks, networks — never OpenShift's `namespace` or VMware's `cluster` (ADR-016). Once placement selects a
provider, that provider requires fields the intent never carried. **Where does the value come from, and how
is the right one chosen?**

The field is provider-specific, so it can only be resolved *after* placement — the provider isn't known until
then. While working this through, one alternative was raised — teach the *data* to select itself:

- **Self-selecting data** — attach `use-when {provider, type}` labels to values in a layer and have the
  assembly engine match those labels against the placement result to pick a value ("label mechanics for
  data"). This would add a new post-placement *data-activation* step.

The original model already covers the need without it, via the mechanism it always intended:

- **A policy resolves the value from governed data** — a post-placement enrichment policy reads governed
  data, selects the value for the chosen provider, and injects it. Only mechanisms that already exist.

## Decision

**Affirm the original model, stated explicitly for the provider-required-field case:** provider-required
inputs not carried by intent are resolved by a post-placement enrichment policy that reads governed data.
Layers stage the data; policies refine and validate it. This is not a new design — it is the layers/policies
split (§1a) applied to this case, and the decision on record is to keep it and **not** add a self-selecting-
data primitive.

- **Layers hold required and relevant information** — the values themselves (a tenant or platform layer, or a
  governed mapping keyed by provider and resource type), authored as data under the standard layer model. A
  layer answers *"what values are available?"* and nothing more. Layers set the stage.
- **A policy makes the decision** — a post-placement (`placement_phase: post`) transformation policy (Step 7;
  `policy-contract.md` §12) reads that data, selects the value for the selected provider, and injects it into
  `provider_extensions`. The policy answers *"given the chosen provider, which value applies?"* — an explicit,
  ordered, auditable rule. Policies refine and validate.
- **One generic policy scales by data, not by rules** — a single "resolve provider-required inputs from the
  mapping" policy covers every field and provider; adding a provider is a new data row, not a new rule.
- **Missing data fails prescriptively** — if the mapping has no entry for the selected provider/type, the
  policy gates with a reason ("no namespace mapping for OpenShift VMs"), surfaced at reserve (ADR-011). A
  coverage check at provider registration / policy activation asserts every provider-required field has a
  fill path, so the gap is caught at config time, not on a user's request.

**Considered and declined — self-selecting data.** Its only advantage was "pure data, no policy" — but that
is exactly what makes the selection implicit: the engine matches whatever labels happen to be in the pool,
and an absent or ambiguous label is a silent miss. It also adds a post-placement data-activation step the
model does not otherwise need. The original model already keeps the value as data (in a layer) *and* makes
the selection prescribed (a policy), with no new primitive — so the label mechanic is unnecessary.

**The principle.** *Layers set the stage for data; policies refine and validate it.* This keeps
`layering-and-versioning.md` §1a honest — a static value stays data (in a layer), and the only *logic*
(selecting and injecting it for the chosen provider) is a policy — and it simplifies layers to what they do
best: hold required and relevant information.

## Options considered

- **(A) Self-selecting data — `use-when` labels resolved post-placement.** Rejected: a new primitive, and
  implicit selection from a pool reintroduces silent-miss risk.
- **(B) [chosen] A policy resolves the value from governed data.** No new primitive (post-placement policies
  and governed layers already exist); selection is explicit and auditable; the value stays data.
- **(C) Put the provider-specifics on the type, or require them from the consumer.** Rejected by ADR-016
  (breaks portability) and by the intent model (never *required* of the consumer; optional at intent, flagged
  non-portable).

## Consequences

- **No new spec primitive** — Step-7 transformation policies and the layer model already carry this.
- **The data/logic split is preserved** — values are data; the selection is the only logic.
- **Prescribed, auditable, complete** — one rule per resolution, gated on missing data, backed by the reserve
  gate and a config-time coverage check.
- **Layers get simpler** — required and relevant information, not conditional logic.
- **Portability stays honest** — a provider-specific value applied to a request flags it non-portable at
  application (ADR-016; `PRV-010`), while the governed mapping can cover many providers at once.
- **Flow doc updated** — `docs/flows/request-realization.md` collapses "a layer default" and "an enrichment
  policy" into one story: the value lives in a layer, a policy selects it; a plain layer default still serves
  fields that aren't provider-conditional.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the governed values in a layer (required + relevant information); `provider_extensions` as
  the home for what the policy injects.
- **Policy (DCM/org):** the post-placement enrichment policy that selects and injects the value, and gates
  when the mapping is missing.
- **Provider:** declares what it requires (the required-data schema — the definition of "enough") and
  validates at reserve.
