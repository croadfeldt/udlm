# Research brief: is Base / Type / Provider enough?

**Type:** validation brief (decision support — not normative). **Written for a separate working
session**, to be run with the maintainer.
**Date:** 2026-08-23 · **Method:** test the three-tier class model against a real use-case corpus
(the DAV review console, `croadfeldt/dav`) rather than against reasoning alone.
**Feeds:** ADR-038 (scoped Base/Type/Provider Classes; "Naming depth — unbounded, but governed"),
`registry/class.schema.json`, `docs/spec/contracts/provider-contract.md` (capability declaration),
and the spec section that does not yet exist (see *What this unblocks*).

## The premise under test

**Three class tiers are enough. No real consumer or provider need requires a fourth level.**

Stated so it can fail, as three separate claims:

- **H1 — sufficiency.** Every need in the corpus is expressible as Base → Type → Provider, without a
  fourth class segment.
- **H2 — the base-class criterion.** A Base class is earned by a **shared portability contract**:
  the members are things a consumer's intent can move between. Groupings that share no portability
  contract are folders, not base classes.
- **H3 — binding depth.** A provider can advertise support at **Base or Type** directly, without
  authoring a Provider Class. A Provider Class is required only when the provider has
  provider-specific *data* to add.

H3 matters most for H1. If a provider must author a Provider Class to be listed, then every
supported type creates a class, and depth pressure follows mechanically. If a provider can bind at
Type, the third tier stays reserved for genuine provider-specific structure.

## Why it matters

If the premise holds, ADR-038's depth section is amended to a hard cap of three, and the
earns-its-keep test stops being the only thing holding depth down.

If it fails, the counter-example is the more valuable output: it tells us what a fourth tier would
have to *mean*. Base, Type and Provider each carry an assigned meaning — the portability contract,
the thing, the opinion. A fourth level has no meaning left over, and the obvious candidates are
already separate axes (below). A real counter-example would either name a new meaning or show that
one of the three is doing two jobs.

## What is already established — do not re-derive

Measured in `croadfeldt/udlm` at the time of writing:

| Finding | Evidence |
|---|---|
| **The spec does not define the tier model.** 9 passing references across `docs/spec/`, none a definition. `governance/registry-governance.md` delegates outright: *"model (ADR-038 — Base, Type, and Provider Classes composed of shared data elements…)"* | the model lives in ADR-038 (30 mentions) and `class.schema.json` (18) |
| **The provider contract already binds at Type**, and mis-describes itself twice. Both projection lists say "PROJECTION of … Provider Classes" and both list Type classes — `resource_types: [fqn: Compute.VM]`, `supported_definitions: [Automation.OSPatch, …]`. The Process one cites `Automation.OSPatch.EngineBlue` as "the pattern" while listing `Automation.OSPatch` | `docs/spec/contracts/provider-contract.md` |
| **The third tier is nearly unpopulated** — 3 Provider Classes in the whole registry (1 Resource, 2 Process) against 12 Resource bases and 40 Resource types | `registry/classes/**` |
| **Current depth**: 23 classes at one segment, 47 at two, 3 at three. Nothing at four | as above |
| **No base-class criterion is stated anywhere.** Portability appears as a property of a *Type* (`resource-type-hierarchy.md` principle 1) and as a derived consequence (ADR-045: *"portability derived from element scope"*). Neither is a test for what earns a Base | `docs/spec/`, `docs/adr/` |
| **`Compute` is the standing counter-example to H2.** Four children; VM and BareMetalHost narrow its elements, Container and Cluster narrow none. A Container inherits `guest_os` — a portability claim no container provider can honor | `registry/classes/resource/compute/` |

## The filter — what does NOT count as a fourth level

ADR-038 names three cheaper axes, and most apparent depth is one of them. Apply this before
recording any counter-example:

- **Version.** `OCPVirt` v2.0 vs v1.0 — never `OCPVirt.new` / `.old`.
- **Capability advertisement.** Two deployments of the same provider offering different features are
  one class advertising different capabilities, not a class fork.
- **Authority / instance.** Two installations are two provider instances on the authority axis,
  orthogonal to class depth.

A genuine counter-example needs **shared-then-specialized definition structure**: two or more
sub-variants sharing elements, each adding distinct ones, that none of the three axes expresses.

## Method

1. **Get the corpus.** DAV (`croadfeldt/dav`) holds the use-case corpus, the capability roadmap and
   the gap analysis. Access details from the maintainer — do not put estate addresses or host names
   in this repository; the estate-token gate fails CI on them, and these specs are public.
2. **Select.** Take the use cases that imply a resource or process type *and* some specialization of
   it — a provider doing something a peer would do differently. Prefer the ones drawn from real
   deployments over synthetic fixtures for H1; the fixture corpus is useful for H2 and H3 because
   its ground truth is known.
3. **Express each in three tiers.** Base (the portability contract) → Type (the thing) → Provider
   (the opinion). Record what each tier holds.
4. **Record every case that will not fit**, and run it through the filter above. Note which of the
   three axes it turned out to be, if it did.
5. **For H2, test the criterion directly.** For each Base that ends up proposed, ask: can a
   consumer's intent move between its members? Where the answer is no, the grouping is a folder —
   record it, because the existing tree has five bases with zero elements (`Platform`, `Storage`,
   `Identity`, `Security`, `Facility`), and the criterion should classify those consistently.
6. **For H3, test binding.** For each provider in the corpus, determine whether it needs a Provider
   Class at all, or whether naming the Type in its capability declaration is sufficient. A provider
   needing a class *only* to appear in a list is evidence for H3 and against depth pressure.

## What to record

For each case: the use case, the tier assignment attempted, whether it fit, and if not, which axis
it actually was. Ambiguous cases are the interesting output — a case that *could* be read as either
a fourth tier or a capability difference is exactly where the rule needs to be sharper.

Two counts settle the premise: **how many cases needed a fourth level after filtering** (H1), and
**how many proposed bases failed the portability test** (H2).

## What this unblocks

A ruling here feeds four pieces of work, in this order:

1. A normative spec section defining the three tiers — what each is, what may live at each, that an
   opinion is legal only at Provider (NDF-001 depends on this), and that a consumer or provider may
   bind at Base or Type. This is the piece that stops ADR-038 from being load-bearing: a decision
   record is immutable by rule, so a model that lives only there cannot be corrected in place.
2. Portability as the stated base-class test, with `Compute` as the worked example of what it
   catches.
3. A fix to both provider-contract projection comments, so they describe what they already show.
4. An amendment to ADR-038's depth section — the cap — written last, once the spec says what is
   being amended.

## Out of scope

- The `Compute` → `Machine` split and the Container / Cluster re-parent. Those are a consequence of
  H2, not a test of it, and they carry a rename cost (126 references to `Container`, 96 to
  `Compute.Cluster`) that should not be spent before the criterion is ruled.
- Naming. Whether the neutral cluster base is `Cluster` or `ContainerPlatform` is a separate
  question and does not affect whether three tiers suffice.
