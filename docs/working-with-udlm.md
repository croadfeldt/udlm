# Working with UDLM — start here

**What this is.** The front door for everyone who touches UDLM. It routes you by what you're here to do.
UDLM is a portable model of infrastructure *intent* — a versioned, digest-addressable registry of resource
types, Classes, policies, and providers, plus the corpus of use cases and flows that documents how they're
meant to behave. Whatever your role, the same promise holds: **the gates handle the bookkeeping so people
can spend their attention on judgment.**

## What are you here to do?

### ▸ Build something *in* the model — a resource type, Class, process, policy, provider, reference data
You're an **author**. Start with the authoring flow — the map of how any artifact goes from idea to merged
— then the HOWTO for your kind.
- **[docs/authoring/authoring-flow.md](authoring/authoring-flow.md)** — the process, end to end, for a first-timer.
- **[docs/authoring/README.md](authoring/README.md)** — pick your artifact kind → its step-by-step HOWTO.

### ▸ Review someone else's contribution
You're a **reviewer**. CI already proves the artifact is valid and complete; your job is the judgment CI
can't make — is it UDLM or DCM, did it reduce-to-existing, should it exist, is it legible.
- **[docs/reviewing.md](reviewing.md)** — what CI guarantees, what only you can judge, and how to say it.

### ▸ Build a system that *uses* the model — a control plane, a provider, a dashboard, another tool
You're a **consumer / system builder**. You read and build on the model rather than authoring registry
artifacts; you declare and pin what you read.
- **[docs/consuming.md](consuming.md)** — how to read it, consume it safely, and extend it as a provider.

### ▸ Contribute to the project — the process, expectations, and guidelines
You're a **contributor**. Here's how contribution works: the PR lifecycle, what's expected, and the
discipline that keeps the model coherent.
- **[docs/contributing-guide.md](contributing-guide.md)** — the on-ramp; expectations, PR process, guidelines.
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — the canonical rules the on-ramp routes to.

## The one thing that's true for all four roles

*Write for a reader who wasn't there* (DOC-001). Every artifact — a spec, an example, a use case, a flow,
an ADR, a review comment — is read by someone without your context. The gates verify that a contribution is
**valid, complete, and internally consistent**; the DAV analysis measures whether the corpus is
**coherent** against the model. Neither writes the clear sentence. That's always a person's job — which is
the whole point of automating the rest.

## The deeper map

- **The model itself** — `registry/` (resource types, Classes, instances, schemas) + `registry/*.schema.json`.
- **The corpus** — `use-cases/` (scenarios) + `docs/flows/` (lifecycles).
- **The rationale** — `docs/adr/` (the decisions, each row in [docs/adr/README.md](adr/README.md) carrying its gist).
- **The gates** — `tests/` + `.github/workflows/validate.yml`; run them all with `./scripts/signoff.sh`.
