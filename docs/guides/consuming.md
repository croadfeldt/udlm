# Building a system on the model — the consuming guide

**What this settles:** how to build a system that *reads and builds on* UDLM — a control plane, a
provider, a dashboard, a generator, a graph ingest — without coupling yourself to a shape that will
shift under you. Read this if you consume the model; if you author registry artifacts, that path is
[`authoring/README.md`](../authoring/README.md). The one promise: **read the right plane, declare what
you read, and pin it — then a registry change that would break you fails in the registry's own CI
naming you, not later in your runtime.**

**In one breath.** UDLM is a portable, versioned, digest-addressable registry of resource types (each
with a schema, a worked example, and the use cases and flows that document how it is meant to behave),
Classes, the estate graph, and the corpus. You build against it by finding a type's schema, its
example, and its coverage block to learn intended behavior; reading the **intent** plane or the
**realized** plane deliberately (they are separate); declaring your read surface in a one-file consumer
manifest; and pinning each type you read by version or digest. If you go further and *realize* intent,
you do it as a provider at the naturalization boundary — you wrap a native backend and report realized
state back; you never push implementation mechanism into the portable model.

---

## 1. What the model gives you

Four things you can build on, all portable across any conformant implementation:

- **Resource types** — the declarative shapes for the things a system provisions (a VM, a Volume, a
  Database, a DNSZone). Each type is authored as a class in `registry/classes/` and served as a compiled flat spec in `registry/generated/`, which validates
  against [`registry/resource-type-spec.schema.json`](../../registry/resource-type-spec.schema.json), and
  ships a worked example plus the corpus that documents its intended behavior (§2).
- **Classes** — the Base/Type/Provider scoped-Class layer under `registry/classes/`, validating against
  [`registry/class.schema.json`](../../registry/class.schema.json). A Class is how one shape specializes
  across scopes without forking the type.
- **The estate graph** — entities bound by typed dependency edges. The entity model is in
  [`docs/spec/foundations/resource-service-entities.md`](../spec/foundations/resource-service-entities.md); how edges and
  dependencies are modeled is in [`docs/guides/dependency-modeling.md`](dependency-modeling.md). This is what a
  dashboard or a graph explorer reads.
- **The corpus** — the use cases (`use-cases/`) and flows (`docs/flows/`) that document *intended
  behavior* as executable scenarios: a happy path, a refusal, a composite. This is the model telling you
  what it is supposed to do, not just what fields it has.

Everything above is **portable** (no implementation's runtime is baked in — ADR-008, the peer test:
*could an independent conformant peer decide this differently and still be valid? yes → it isn't in the
substrate*), **versioned** (semver, with the publish law — §4), and **digest-addressable** (every
published revision has a recorded sha256 — §4).

---

## 2. How to read it — schema, example, story

Before you build against a type, read three things co-located with it, in order. They answer *what
shape*, *what a real one looks like*, and *how it is meant to behave*.

| To learn… | Read | Where it is |
|---|---|---|
| the **shape** (fields, required, refusals) | the type spec's `spec` (a JSON Schema) | `registry/generated/<category>.<type>.json` |
| what a **valid one looks like** | `spec.examples` — the worked example, CI-validated against the spec (ADR-055) | inside the same spec, under `spec.examples` |
| how it is **meant to behave** | the `coverage:` block — its use cases + flows | top-level `coverage:` on the same spec |

The `coverage:` block is your entry point to intended behavior. On `Compute.VM`, for
example, it names three use cases (a standard provision, a provider-failure *refusal*, a composite
VM-with-volume) and the flows that walk them. Read the refusal case first when you integrate — a type's
must-reject contract (typed, actionable, non-leaking, auditable) is where the real behavior lives, and
it is the case a naive integration gets wrong.

The registry layout you will navigate:

| Directory / file | What it holds |
|---|---|
| `registry/generated/` | the served type specs, compiled from the classes (compute.vm, network.vlan, …) |
| `registry/classes/` | the authored surface — the scoped Classes (ADR-061 hierarchy) |
| `registry/examples/` | worked instances of records (policies, layers, decision records, accreditations) |
| `registry/*.schema.json` | the meta-schemas every artifact validates against |
| `registry/consumers/` | the consumer manifests — where you declare *your* read surface (§3) |
| `registry/pin-manifest.json` | the generated map of every published `thing → version → digest` (§4) |
| `use-cases/` · `docs/flows/` | the corpus — scenarios and lifecycle flows |

A fast index of the whole tree is in [`docs/file-index.md`](../file-index.md); the human-readable catalog
of every type is [`registry/TYPE-CATALOG.md`](../../registry/TYPE-CATALOG.md).

---

## 3. How to consume it safely

Three disciplines. The first is which data you read; the second and third are how you keep the registry
honest with you.

### Read the right plane — intent vs realized

The model separates what was *asked for* from what *exists*. Intent (declarative: what you want) flows
`intent → requested`; a **provider populates the realized plane** with what it actually built —
discovered runs alongside as ground truth. The full lifecycle is in
[`docs/spec/foundations/four-states.md`](../spec/foundations/four-states.md); the realized shape is
[`registry/realized-entity.schema.json`](../../registry/realized-entity.schema.json) (narrated in
[`registry/REALIZED-ENTITY.md`](../../registry/REALIZED-ENTITY.md)).

Read the plane your job needs, and know which it is. A control plane assembling a request reads
**intent**. A dashboard reporting what is running, or a drift check, reads **realized/discovered**. A
provider reads intent and *writes* realized. Reading realized fields (provider-assigned IDs, IPs, UUIDs)
as if they were intent — or trusting intent as if it were the running truth — is the integration bug
this distinction exists to prevent.

### Declare your read surface (ADR-044)

Put one manifest in `registry/consumers/<you>.yaml` naming the types you read. This is not paperwork —
it is what lets a registry change that would break you fail in the registry's CI, naming you, instead of
failing silently in your runtime later. The motivating incident was exactly that: a control-plane
generator mapped 5 of 46 types with no warning for the rest, found by a code sweep, not by a gate
(ADR-044 — consumers declare what they read, the registry gates on it).

The manifest shape, gated by
[`tests/check_consumer_conformance.py`](../../tests/check_consumer_conformance.py):

```yaml
consumer:
  name: your-system
  repo: org/your-system
  description: One line on what you do with the model.
consumes:                                    # XOR consumes_all_types: true
  - resource_type: Compute.VM
    noted_version: 0.6.4                      # the registry version you last verified against
    noted_digest: sha256:<64 hex>             # optional — the exact bytes (see §4)
schemas:                                      # optional — registry schema files you read
  - registry/resource-type-spec.schema.json
coverage: declared                            # `verified` is your own promotion, gated in your CI
```

Provide exactly one of `consumes` (a named list) or `consumes_all_types: true` (for an envelope-level
reader — a graph ingest, the analysis engine). The gate enforces three invariants: every named type
**exists**; no `noted_version` runs **ahead** of the registry (a claim to have verified against a
registry that does not exist); and every registry type is consumed by ≥1 manifest **or** acknowledged in
`registry/consumers/unconsumed.yaml`, which the gate regenerates and diffs so the acknowledgment can
never drift silently. Start at `coverage: declared`; `verified` is reserved for a consumer that gates
its own conformance against its manifest in its own CI — it is your promotion to make, never the
registry's to grant.

### Pin what you read (ADR-051)

A `noted_version` is a pin. The registry runs under the **publish law**: a `uuid` is frozen identity and
never changes, any content change bumps the `version`, and a published `(identity, version)` is never
republished with different bytes (npm's rule). That is what makes `thing@version` mean something. The
grammar is OCI/git — **tag for humans, digest for proof**:

- `thing@version` (e.g. `type:Compute.VM@0.6.4`) — human-legible; resolves to a recorded
  digest through [`registry/pin-manifest.json`](../../registry/pin-manifest.json), the generated referrer
  mapping every published `thing → version → sha256`.
- `thing@sha256:<hex>` — the exact bytes, verified directly. Carry it as `noted_digest` on the entry
  above when you need proof, not just a label (a high-stakes profile such as `fsi` may *require* digest
  pins).

The digest is a sha256 over the RFC 8785 canonical form, so it names the document's *meaning*, not its
whitespace, and JSON and YAML serializations of one document hash identically. It is generated by
[`registry/tools/generate_pin_manifest.py`](../../registry/tools/generate_pin_manifest.py); an artifact
never carries its own digest (the referrer rule). One consequence worth building on: `coverage:` and
`spec.examples` are **excluded from the identity digest**, so a new use case against an unchanged spec,
or a refreshed example, does not rev the type's version — a docs-only refresh will not move your pin.

---

## 4. How to extend it as a provider — the naturalization boundary

If your system does not just read intent but *realizes* it, you build a **provider**, and you work at
the naturalization boundary. A provider **naturalizes** — translates a native (vendor) representation
*into* the unified model — and **denaturalizes** — translates realized state back out to the native
form (the terms are defined in [`GLOSSARY.md`](../../GLOSSARY.md)). The contract you implement is
[`docs/spec/contracts/provider-contract.md`](../spec/contracts/provider-contract.md).

The load-bearing rule: **you wrap a native backend and populate the realized plane; you do not put
implementation mechanism into the portable model.** UDLM is the portable intent plus the estate graph; a
implementation (DCM, or any independent peer) is the engine that makes intent real. The line is the ADR-008
peer test — *anything a conformant peer could do differently is implementation, and stays out of the
substrate*; the tenet form is T8 in [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (*adopt tools by reference —
wrap the mature tool as a Provider, don't have the control plane reimplement it*). Concretely, a
provider MUST report realized/discovered state back per resource with an identity correlation (your
native id ↔ the UDLM `uuid`) — without that read-back the control plane is blind to reality and cannot
own the lifecycle. The scale-of-integration model for that read-back and config projection is **DCM
ADR-023** (in the DCM repo, cited throughout `provider-contract.md`; note this repo's own DCM ADR-023 is a
different subject — host networking as data).

What this buys you: your backend's specifics stay yours, the portable model stays portable, and any
other conformant consumer reads the realized state you report without knowing your tool exists.

---

## 5. Where to go next

- **You need a type the model doesn't have** → author it: [`authoring/README.md`](../authoring/README.md)
  and the flow in [`authoring/authoring-flow.md`](../authoring/authoring-flow.md) (reduce-to-existing
  first; a new mechanism must earn its place).
- **You're reviewing a consumer or a contribution** → the reviewer guide,
  [`reviewing.md`](reviewing.md) (what CI guarantees, what only you judge), backed by the review sweep in
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md) § "The review sweep".
- **You want the deep rationale** → the ADR index, [`docs/adr/README.md`](../adr/README.md). The four that
  bound this guide: **ADR-008** (the UDLM/DCM boundary and the peer test), **ADR-044** (consumers declare
  what they read), **ADR-051** (identity/version/digest and the pin grammar), **ADR-055** (in-spec
  examples).
- **You're a user submitting intent, not building on the model** → the driver's handbook,
  [`docs/guides/consumer-perspective.md`](consumer-perspective.md): what you submit, what you get back, errors,
  retries, conformance discovery.
