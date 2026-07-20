# UDLM/DCM Naming Charter (Proposed)

> **Status: Proposed — a straw man for engineering review.** The goal is **one cohesive naming pass before
> the 1.0 tag, then a freeze.** This charter proposes the canonical vocabulary, shows how the axes relate,
> and batches the renames still outstanding. It binds nothing until ratified. Opinionated on purpose — react
> to it, don't start from a blank page.

## Why now

Every individual term is justified, but the vocabulary is not a cohesive *system*: several axes overlap
(`family` / `nature` / `archetype`), and terms have churned (Blueprint → Template, Atomic/Composite →
`single`/`multi`, Composite Service → Template). **Incremental** renaming is the churn that erodes adopter
trust. **One** deliberate pass is the cure. Pre-1.0 is the only cheap window — after the tag, terms are
cited, depended-on, and externally adopted, and renaming is breaking. So: settle it once here, publish the
map, and **freeze at 1.0**.

## The one lifecycle, at two scales

There is one shape. Don't invent parallel vocabulary for it.

| Entity scale (four states) | Assembly scale | Role |
|---|---|---|
| **Intent** | **Pattern** | the reusable, design-time desire (type level) |
| **Requested** | **Template** | the resolved, orderable definition |
| **Realized** | **System** | the running instance |
| **Discovered** | — | observed reality with no intent (joined by adoption) |

`Intent → Requested → Realized` (ADR-030) *is* `Pattern → Template → System` (ADR-033) one scale up. The
transitions are the same act — **Converge**.

## The classification axes (proposed — collapse the overlap)

The core simplification: **`nature` is the one fundamental axis; `family` and `archetype` are a view and a
preset over it, not parallel classifications.** Today three fields draw nearly the same partition.

```mermaid
flowchart TD
    NAT["nature — THE axis<br/>maintained-state · work-product · curated"]:::axis
    NAT --> AR["archetype — friendly presets over (nature + timeline + terminal)<br/>Resource · Credential · Inventory · Identity · Process · Knowledge"]:::preset
    ET["entity_type — shape (orthogonal)<br/>single · multi"]:::orth
    RT["resource_type — the specific type (orthogonal, finest)<br/>Compute.VirtualMachine · Automation.AnsiblePlaybook · …"]:::orth
    classDef axis fill:#dbeafe,stroke:#2563eb,color:#111
    classDef preset fill:#ede9fe,stroke:#7c3aed,color:#111
    classDef orth fill:#f3f4f6,stroke:#6b7280,color:#111
```

| Axis | Values | Answers | Proposal |
|---|---|---|---|
| **nature** | maintained-state / work-product / curated | what *kind* of lifecycle — reconciled? terminal? | **the axis**; reconcilability hangs off it |
| **archetype** | Resource · Credential · Inventory · Identity · Process · Knowledge | the friendly, queryable **preset** over (nature + timeline + terminal) | **a view of nature**, not a peer axis |
| **entity_type** | `single` / `multi` | constituent **shape** (owns constituents?) | **keep** — orthogonal |
| **resource_type** | `Compute.VirtualMachine`, … | the **specific** type | **keep** — orthogonal, finest |

**What this retires:** `family` (Resource / Process / Knowledge / Access) as a *separate* axis. The
state-vs-execution distinction it drew (ADR-027) *is* the nature distinction — Resource = maintained-state,
Process = work-product, Knowledge = curated. `family` was a third name for the partition `nature` already
draws. It may survive as a **derived view/alias** of nature (query convenience) rather than a stored field —
that's a ratification detail.

**The one decision that unlocks the axis** (task #55): is `work-product` a *full* nature, or a
maintained-state with a one-shot intent and a terminal condition? This is the same question as "does a
Process reconcile?" Settle it and the axis locks. *(`Access` / `Identity` folds in as a maintained-state
archetype — an identity is maintained, not one-shot.)*

## The tiers and the triad (unchanged — just naming them once)

- **Data · Policy · Provider** — the invariant decomposition. UDLM = Data (substrate); DCM = Policy
  (realization); Provider = mechanism (wraps tools, T8). Every decision decomposes across all three.
- **Pattern → Template → System** — roles, not new things (above). **Composite Service = Template**
  (ADR-034); **Blueprint** is retired → Template.

## Canonical glossary (proposed) + retired aliases

| Canonical | Means | Retired / folded names |
|---|---|---|
| **Template** | the orderable, resolved composite definition (Requested tier) | Blueprint · Composite Service (catalog item) |
| **System** | the realized instance of a Template | Composite Entity |
| **Pattern** | the reusable, design-time design (Intent, type level) | — |
| **nature** | the lifecycle-kind axis (maintained-state/work-product/curated) | *family* (folds in as a view) |
| **archetype** | friendly preset over nature | — |
| **entity_type** `single`/`multi` | constituent shape | Atomic / Composite |
| **edge_type** | the relationship-kind field | `kind` (for edges) |
| **Converge** | the single lifecycle act | realize/reconcile/rehydrate/teardown (colloquial shortcuts, not distinct acts) |

*(Note a residual collision to resolve: "family" is also used for a **rule-ID prefix family** — an unrelated
sense. If `family` is retired as an entity axis, keep it only in the rule-ID sense, or rename that too.)*

## Batched renames still to land (pre-1.0)

These land together, then the freeze applies:

- **Composite Service → Template**, Composite Entity → System, `CMP-*` → `TPL-*` — ADR-034 (gated on eng ruling).
- **`family` → `nature` reconciliation** — this charter (gated on the work-product decision above).
- *(already landed: Blueprint → Template · Atomic/Composite → `single`/`multi` · edge `kind` → `edge_type`.)*

## Known term conventions to reconcile

Real-world usage of these words varies by group — the charter should map onto it, not ignore it.

- **"Blueprint."** *This group* uses "blueprint" ≈ a **reusable design** — i.e. our **Pattern**. vRealize /
  Aria and Azure use "blueprint" ≈ a **deployable definition** — i.e. our **Template**. The word spans *both*
  tiers, which is exactly why it is retired here: adopting it for either tier collides with the other group's
  meaning. **Open question for eng:** do we adopt **"Blueprint" for the Pattern tier** (rename `Pattern →
  Blueprint`, matching this group's usage), or keep `Pattern` and treat team-"blueprint" as an informal alias
  mapped in conversation? We *cannot* use "Blueprint" for the Template tier without re-colliding with the
  vRA/Azure sense.
- **"Validated Pattern"** (Red Hat) — a *deployable, tested* composite ≈ our **Template**, **not** our
  (abstract) Pattern. When citing it, map it to Template.

These are the vocabulary the eng review reconciles alongside the `family`/`nature` collapse — the point of the
charter is to land on names that match how teams already speak, then freeze.

## The freeze

**At the 1.0 tag the vocabulary is frozen.** After that, a new term or a rename is a **breaking change**
(VERSIONING) and requires a **charter amendment** (a Proposed ADR that updates this doc). This charter then
becomes the canonical glossary — the single place the vocabulary lives, so coherence is in a doc, not in
anyone's head.

## Alternatives considered

- **Keep `family` + `nature` + `archetype` as three axes** — rejected: three names for ~one partition is the
  incoherence this charter fixes (the same "two terms for one objective" smell as Composite Service).
- **Freeze the current terms as-is** — rejected: locks in the overlap permanently.
- **Keep renaming incrementally** — rejected: churn without a charter erodes adopter trust; one pass + freeze
  is the discipline.
