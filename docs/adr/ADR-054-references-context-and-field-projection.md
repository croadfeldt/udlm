# UDLM ADR-054: Orthogonal data — the references-context axis, field projection, and layer scoping

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); extracted from
ADR-038 while both are Proposed, so the scoped-Class paradigm and this mechanism ratify separately
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited
once with what it settles. ADR-038 — the scoped-Class hierarchy (`SharedDataElement`, the `§10`
dotted coordinate + dual anchor this builds on); this ADR is the third relationship axis alongside
its *is-a* and *has-a*. ADR-012 — data references point at immutable records (the linkage this
classifies and projects). ADR-041 — the policy information firewall *over* projection (it adds
`PROJ-P6` to the invariants below and governs data entering by reference). `foundations/layering-and-versioning.md`
— the assembly/layer model (`covers`/`skip` extend it). T1/T2 + ADR-023 — the naturalization
boundary the anti-exfil invariants protect.

## Context

The Class hierarchy is *is-a* (ADR-038); a Composite Service is *has-a*. A resource also carries
**orthogonal context** — data *about* it that is not part of its own definition: a Data-Center info
bundle, an app profile, a compliance bundle. Modeled naively this becomes either an assembly layer
(it isn't — DC power/zone data is not part of the VM's spec) or a bare untyped pointer (it can't be —
the link has a governed nature and must feed policy). And referencing a bundle keeps the record
concise, but assembly often needs *one specific field from the target* in the resource's own realized
spec (a bare-metal's network config needs its DC's `network.fabric_id`). The linkage, the addressing,
and the assembly all exist; what was missing is the axis that ties them together and the projection
that carries a target field *along the edge*. This ADR decides them. Extracted from ADR-038 so the
Class paradigm and this mechanism ratify independently — ADR-041 already builds on it as a discrete
thing.

## Decision

**1. References-context is a classified edge, not a layer.** Orthogonal context is a
**classified, dereferenceable edge** in the relationship graph (relation nature = `context` +
strength, dual anchor, `§10` coordinate) — never an assembly layer, never a bare pointer.
**`reference_data` is retired from `layer_type`**: context is never merged into the assembly, so it
was never a layer — it is a **linked entity** reached by an edge. `layer_type` is now assembly-only
(`base`/`core`/`intermediate`/`service`/`request`/`policy`). One entity, many linkers — a Data-Center
info bundle is one entity every resource in the DC links via a `located-in` (context) edge; no
duplication, and the edge carries a nature a bare reference could not.

**2. The navigational coordinate — project a target field along an edge.** A `§10` coordinate may
reach its anchor by **traversing a classified edge from self**:
`self.located-in.network.fabric_id` = self → the `located-in` edge → a field-path on the DataCenter
at its far end. This is the OData navigation-property / RDF property-path shape — a graph hop in the
address, not a new construct (edge + coordinate + layer + dual anchor + governed dereference).
Resolving it yields a **derived layer value**, landed in the effective spec with provenance (LAY-008)
and the dual anchor (the immutable pin captures the target field *at realization* — reproducible; the
named head follows current). On a later target change: rehydrate replays the pin; `impact_report`
surfaces the linker as affected (the projection recorded a *data* dependency); a governed re-resolve
repoints and re-pins. `nature: context` means it never gated the linker's *lifecycle*, only its data.

**3. Projection policy-safety — a projection feeds policy, never skirts it (`PROJ-P1..P5`).** A
projection is a layer-contributed value, so policy over the merged result sees the concrete value
exactly as if typed. Five invariants (ADR-041 adds `PROJ-P6`, the firewall admission):
- `PROJ-P1` **resolve-before-policy** — projections resolve within the merge; policy sees concrete
  values, never unresolved coordinates.
- `PROJ-P2` **target-egress gate** — the dereference runs the *target's* egress/sovereignty policy
  (address ≠ dereference), not only the source's — the anti-exfil guarantee.
- `PROJ-P3` **mandatory provenance** — source + edge + anchor recorded for every projected value;
  nothing enters the spec from nowhere.
- `PROJ-P4` **re-run policy on replay** — rehydration re-evaluates *current* policy; a pin reproduces
  data, never exempts it from today's rules.
- `PROJ-P5` **governed edge nature** — the relation's nature is validated, not self-asserted; no
  downgrading a dependency to `context` to escape gating.

**4. Two-sided layer scoping — injection is the intersection of publish ⋈ subscribe.** A layer
injects data into a request during assembly — a static value (`encryption: required`) or an
edge-projected value (§2). Which layer reaches which request is a two-sided handshake, both sides
speaking the one `§10` selector language:
- **Target (the layer declares):** `covers` — a `§10` selector list over authority +
  `Category.Type.Provider` + attribute predicates (*which entities*; a Kubernetes label selector is
  just this over `.labels`, not a parallel construct); `applies_on` — the lifecycle operations it
  injects during (*which processes*).
- **Source (the request/profile declares):** `from_layers` — a selector over the layer graph naming
  the layers a request draws from (usually inherited from its profile; this **bounds** assembly — a
  tenant-A request draws tenant-A's layers even if a tenant-B layer's `covers` would match); `skip` —
  the negative form, governed (freely skippable for defaults; `narrow_only`/compliance require
  attested break-glass, audited).
- **Injection = the intersection:** `L` injects into `R` iff `R.target ∈ L.covers` **and**
  `R.operation ∈ L.applies_on` **and** `L ∈ R.from_layers` **and not** `L ∈ R.skip`. `covers` says
  *who may*; `from_layers` says *who does* — both required, neither alone the boundary. Because
  injection lands data into the spec it is an **ingress crossing**: `PROJ-P6` admission applies
  (ADR-041). `covers`/`skip` are Data (the declaration); the match is Policy (DCM's assembly engine).

## The three relationship axes (all existing mechanisms)

| Axis | Relationship | Mechanism |
|---|---|---|
| **is-a** | a Class specializes a definition | `extends` (Base → Type → Provider) — **ADR-038** |
| **has-a** | a Composite orchestrates constituents | `catalog-item` constituents (`entity_type: multi`) |
| **references-context** | a resource links to orthogonal data / entities | a classified, dereferenceable edge (nature + strength, dual anchor, `§10` coordinate) — **this ADR** |

## Worked examples

**DC info projected into a bare-metal request** — the linkage (edge), the projection (navigational
coordinate), and the landing (layer, provenance, pin):
```yaml
# ① DataCenter entity (rev-42)                          # ② concise bare-metal request (intent)
$id: acme.example/DataCenter#dc-east                     class: Compute.BareMetalHost
network:  { fabric_id: fab-7 }                           relationships:
power:    { feed: "A+B" }                                  - relation: located-in    # classified edge
location: { residency: state.mn }                            target: acme.example/DataCenter#dc-east
                                                             nature: context         # not a lifecycle dep
# ③ a layer projects DC fields via the edge
layer: core/baremetal-dc-binding
covers:     [ Compute.BareMetalHost.* ]                  # target: entity
applies_on: [ provision, rehydrate ]                     # target: process
fields:
  network.uplink_fabric: { value: self.located-in.network.fabric_id }
  placement.residency:   { value: self.located-in.location.residency }   # sovereignty flows in
# ④ realized spec, with provenance + pinned anchor
network:   { uplink_fabric: fab-7 }     # ⟵ via located-in  [pin: dc-east@rev-42]
placement: { residency: state.mn }      # ⟵ via located-in  [head: dc-east]
```

**Two-sided injection** — static and projected are the same mechanism, differing only in whether a
field's value is a literal or a navigational coordinate:
```yaml
layer: core/compliance-encryption
covers: [ Compute.*, Storage.* ]   applies_on: [ provision, migrate ]
fields: { encryption: { value: required, authority: immutable } }
# request Compute.VM web-01, operation provision, profile acme/sovereign
#   → from_layers ⊇ core/compliance-*  ⇒ web-01 ∈ covers ∧ provision ∈ applies_on ∧ layer ∈ from_layers
#   ⇒ encryption: required (immutable) merged, with provenance
```
Source scoping holds a tenant boundary: `tenant-a/*` and `tenant-b/*` both `cover: Compute.VM.*`, but
a tenant-A request's `from_layers` includes only `tenant-a/*` — it never receives B's, even though B's
`covers` matches.

## Prior art / standards alignment

| Piece | Matches |
|---|---|
| Field projected along an edge (navigational coordinate) | **OData** navigation properties / `$expand`; **RDF** property paths; **JSON Pointer** fragments |
| Classified edge with governed dereference | **Linked Data** (URI identity, governed dereference); OData `@odata.id` |
| Two-sided `covers` ⋈ `from_layers` scoping | **DNS** wildcards; **LDAP** DN + filters; **OData** `$filter`; AMQP/MQTT topic routing (publish ⋈ subscribe) |

Convergence signal (ADR-023's argument): independent standards agreeing is the reason to adopt the
shape, not invent. The synthesis — sovereignty-gated dereference over a portability-scoped graph — is
UDLM's own.

## Data · Policy · Provider · UDLM/DCM boundary

- **Data (UDLM):** the classified edge, the navigational coordinate, the `covers`/`applies_on`/
  `from_layers`/`skip` declarations, the dual anchor. Portable record shape.
- **Policy (DCM):** the assembly-engine match (injection intersection), the dereference, the
  `PROJ-P1..P6` enforcement, the skip authorization.
- **Provider:** none dispatched by a projection; the target's provider owns the projected field's
  source of truth.

Per the peer test (ADR-008): UDLM defines the edge, the coordinate grammar, `covers`/`skip`/
`from_layers`, and the projection invariants (a peer MUST honor); DCM's assembly engine computes the
match, resolves projections, and enforces the invariants (a peer MAY differ).

## Consequences

- The paradigm's third axis is named and separable from the Class hierarchy, so a reviewer can ratify
  one without the other — and ADR-041's citations (`§references-context`, `PROJ-P1..P6`) now resolve
  to a decision of their own instead of a section of ADR-038.
- `reference_data` leaving `layer_type` makes "context is a linked entity, assembly is layers" a hard
  line rather than a convention.
- One filter mechanism (`§10` selectors) serves injection scoping, addressing, query, and event
  routing — no parallel construct for any of them.

## What this does not decide

The `§10` coordinate/addressing grammar itself (ADR-038 + the scoped-class-hierarchy design notes);
the assembly precedence/override/`narrow_only` model (`foundations/layering-and-versioning.md`); and
the firewall admission `PROJ-P6` and cross-domain guard (ADR-041). The JSON-Schema shapes (the edge
`nature`, `covers`/`applies_on`/`from_layers`/`skip` on the layer/request envelopes) follow as an
implementing PR once ratified.
