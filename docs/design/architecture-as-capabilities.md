# The architecture is a Pattern — a proposal

**What this settles:** that the implementation tier gets a *name and a shape* independent of any
product, and that the shape is one UDLM already has. It proposes no new primitive.

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **ADR-033 (amended)** — Pattern → Template → System are two definitions and one instance, and *which one a composition is* is **derived**: a composition naming a `Capability` is a Pattern; one whose every part names something a provider can realize is a Template.
- **ADR-008** — the peer test: could an independent implementation do this differently and still be valid? Yes → the implementation's; no → the substrate's.
- **`PRV-004`** (provider-contract §10) — a peer implementation *is a typed provider*; federation is the provider abstraction applied across peers, not a second mechanism.
- **`CONFORMANCE.md` §4** — a conformance declaration already carries `level: full | partial` with `exclusions`.
- **ADR-067** — a composition nobody offers is a `composition` record; offering it makes it a class.

---

## The problem, in plain terms

**There is no name for the middle tier, so every sentence about it names a product.**

UDLM says what data means. Something has to turn intent into a realized resource — assemble layers,
evaluate policy, place, reserve, dispatch, reconcile. That thing has been called "DCM" throughout,
because DCM is the one that exists.

The cost is measurable. Removing implementation references from the normative tier (#503) touched
**824 lines across 127 files**, and the honest reason there were so many is that authors had two
choices and both were wrong: say **"DCM"** (one product, so no other implementation can read the
sentence) or say **"the control plane"** (a role, not an artifact — nothing you can build against or
declare conformance to).

A provider author reading `provider-contract` could not answer *"what am I building against?"* with
anything more precise than a product name.

## The proposal

**The architecture is a collection of capabilities, strung together through UDLM and the contracts.
An implementation may provide all of them, or some — and a peer completes the rest.**

That is the maintainer's framing, and the finding of this document is that **UDLM already describes
it.** Three tiers, and they are the model's own spine applied to itself:

| | | Is |
|---|---|---|
| **UDLM** | what the data means | **intent** |
| **the architecture** | which capabilities, wired how | **the enriched request** — a definition |
| **an implementation** | those capabilities, running | **realized** |

## Why this needs no new primitive

### An architecture is a Pattern, by the existing derivation rule

ADR-033, already ruled:

> *A composition is a **Template** when every constituent names something a provider can realize; one
> naming a `Capability` leaves the shape open and it is still a **Pattern**.*

An architecture's constituents are **capabilities** — `realize_resources`, `serve_data`,
`authenticate`, `federate`, `execute_workflows`, each already a term in the governed
`provider-capability` taxonomy. Capabilities are Knowledge: curated, never provisioned, never
realized by a provider.

So an architecture satisfies the Pattern test *by construction*, and nothing has to declare it one.
The composition mechanism (`constituents`, `depends_on`, `binds_to`, `composition_visibility`) is the
same one a Template uses.

**This is the finding.** The architecture is not a new artifact needing a new model — it is the tier
the Template work already built, viewed from the implementation side rather than the resource side.

### Partial implementation is already modelled

`CONFORMANCE.md` §4's declaration carries `level: full | partial` and, when partial, **required**
`exclusions` — *"a partial claim that does not say what is excluded is not a partial claim; it is a
full claim with the difficult part left out."*

That is exactly *"an implementation may have all the capabilities built in, or it may be a partial."*
What is missing is only that `exclusions` names **contracts** rather than **capabilities**, which is
a vocabulary change, not a mechanism.

### "Another implementation completes it" is already federation

`PRV-004`: **a peer implementation is a typed provider.** So an implementation lacking
`execute_workflows` does not need a new composition mechanism to borrow it — it sources it from a
peer through the provider contract, exactly as it would source a VM from a virtualization provider.

The composition edge already distinguishes the two cases: a capability you **own** is `contained_by`;
one you **borrow from a peer** is `binds_to`. That distinction is enforced (`CMP-012`), and
`GRP-INV-002` makes it structural rather than stylistic.

## Described in UDLM

A reference architecture is a composition whose parts are capabilities:

```yaml
record_type: composition          # a Pattern: parts name capabilities, so the shape is still open
handle: udlm/architecture/reference-control-plane
state: PROPOSED
constituents:
  - component_id: assemble
    resource_type: Capability          # Knowledge — curated, never realized
    provided_by: self
    failure_effect: required           # no assembly, no request
  - component_id: policy
    resource_type: Capability
    provided_by: self
    failure_effect: required
    depends_on: [assemble]             # policy reads the assembled payload
  - component_id: place
    resource_type: Capability
    provided_by: self
    failure_effect: required
    depends_on: [policy]
  - component_id: realize
    resource_type: Capability
    provided_by: external              # a provider does this; the architecture only requires it
    failure_effect: required
    edge_type: binds_to
  - component_id: federate
    resource_type: Capability
    provided_by: external
    failure_effect: optional           # a single-estate implementation may omit it entirely
    edge_type: binds_to
```

An implementation then declares which of these it provides — and a **partial** one names what it
does not, so a consumer can tell whether a peer is needed before depending on it.

## What this changes, and what it does not

**Changes:** the normative tier gets a subject that is not a product. `provider-contract` stops
saying *"the control plane does X"* and starts saying *"an implementation providing `realize_resources`
does X"* — which is checkable, and which a provider author can build against.

**Does not change:** any mechanism. Composition, capability, conformance declaration, federation and
the provider contract are all in place. This is a naming and an assembly, not a build.

## Open questions

1. **Specification or catalogue?** *"Here are the capabilities an implementation MUST provide"* is
   conformance surface. *"Here are capabilities implementations MAY compose"* is a library. The two
   version differently — the profile-set split (#488) is the precedent, and the same clock argument
   applies: a catalogue moves with what people build, a specification moves with what peers must
   agree on.
2. **Where does it live?** Its own repository on its own version axis, by the rule set in #488 — a
   set with its own lifecycle does not share a release with the spec. But an architecture is closer
   to the substrate than a profile set is, so this is worth arguing rather than inheriting.
3. **Does the capability vocabulary need to grow?** Five terms exist. An architecture strung from
   five capabilities is coarse; the granularity that makes *partial* meaningful is the question —
   too coarse and every implementation is "partial", too fine and the vocabulary is a task list.
4. **What is the conformance unit?** Today a declaration excludes *contracts*. If an architecture is
   capabilities, exclusions should name capabilities — and then "conformant" means *"provides the
   capabilities it claims, to the contracts UDLM defines"*, which is a sharper statement than today's.

## What it would have saved

Stated because it is the evidence, not a rhetorical flourish: the 824-line neutrality sweep existed
because there was no third word. With a named capability set, most of those sentences would have had
a correct subject when they were written.
