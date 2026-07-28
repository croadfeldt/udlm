# UDLM ADR-051: Identity, version, digest — one meaning per field, registry-wide

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); decided 2026-07-25
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles. The doctrine this replaces
(VERSIONING.md § "UUID rotation", now § "Identity, version, digest" — every change to a
uuid-bearing document minted a new uuid); the ADR this amends (ADR-045 — class evolution and
pinning; its pin, provenance, and provider-surface clauses are restated below and marked
amended in place); the reference shape that was already right (ADR-012 — data references
point at immutable records, so an identity pin on one is exact by construction); the
attestation surface that exposed the conflict (`registry/accreditation.schema.json` — an
accreditation binds a provider and capability by uuid); and the gates that enforce the ruling
(`tests/check_identity_integrity.py`, `registry/tools/generate_pin_manifest.py`).

## Context

A UUID can name a *thing* or it can name a *revision of a thing*, and this registry had it
doing both. The versioning doctrine made the uuid the revision: any change to a uuid-bearing
document minted a new v4 uuid, the handle stayed stable, and a "uuid-precise" pin was exact
because each uuid named one immutable set of bytes. Meanwhile the provider and realized planes
documented the same field as stable identity: an accreditation attests a `subject_uuid` and
binds a `capability_uuid`, an identity-escrow record anchors on an entity uuid, and a realized
instance carries the uuid of the thing it is — none of which can rotate without severing what
was attested or anchored. ADR-045 §8 then exported the rotation rule onto the provider plane
("any change to the definition rotates its uuid"), and the follow-up audit caught the
collision: the accreditation's anchor and the rotation token were the same field, so any edit
to a provider definition would orphan every attestation bound to it.

The maintainer ruled the industry-standard resolution, applied consistently across the board:
**UUID is identity, version gives functional relationship data, and change transparency comes
from content digests** — the job the rotating uuid was doing moves to sha256, where the rest
of the industry already keeps it.

## Decision

**1. UUID = identity.** One meaning everywhere: the uuid names the thing, is frozen at
creation, and is never reused — for type specs, providers, capabilities, instances, and
records alike. Nothing about a document's content is ever inferable from its uuid, and no edit
ever changes one.

**2. Version = the semver compatibility contract, plus the publish law.** The bump table and
the pre-1.0 MINOR floor (VERSIONING.md) are unchanged. What is new is stated once and gated:
**(identity, version) is immutable once published.** Any content change ships a version bump
(≥ REVISION); republishing an already-published (identity, version) with different bytes is
refused. This is npm's publish law, and it is what makes a `thing@version` pin meaningful.

**3. Pin grammar: `thing@version` and `thing@sha256:<hex>`, both first-class.** The
human-legible pin names a published (identity, version) pair and resolves to its recorded
digest through the pin manifest; the exact pin names the bytes directly and verifies them.
This is the OCI/git model — tag for humans, digest for proof — and a profile may require
digest pins where the stakes warrant it (fsi).

**4. Digest = sha256 over the RFC 8785 (JCS) canonical form.** A document is parsed (JSON or
YAML — the two serializations of one document digest identically) and canonicalized per
RFC 8785 before hashing, so the digest names the document's *meaning*, not its whitespace.
**The referrer rule (OCI): an artifact never carries its own digest.** Digests live in
generated referrers — the pin manifest (`registry/pin-manifest.json`), compilation and
implementation provenance, attestations, promotion evidence — never in the artifact itself.
What used to be rotation bookkeeping is now recomputation: a change produces a new digest by
construction, with nothing to remember to mint.

*What identity covers.* The digest is taken over the document's **normative** bytes. A small,
named set of **non-normative documentation surfaces is excluded**: top-level `coverage` (the Use
Cases / examples / flows that exercise a spec — rule-36) and `spec.examples` (the JSON Schema
`examples` annotation, which that spec defines as having *no effect on validation* — ADR-055).
Both grow or refresh over a spec's life: adding a UC that exercises an **unchanged** spec, or
refreshing a worked example, must not rev its identity or force a version bump. The strip is one
function (`_strip_nonnormative` over `IDENTITY_EXCLUDED_FIELDS` + `spec.examples`, in
`registry/tools/generate_pin_manifest.py`), consulted by both the pin manifest and the identity
gate, so a docs-only edit is provably digest-invariant. Everything not stripped is identity; the
set is deliberately tiny and additions are an ADR-level call.

**5. Two document families, one uuid meaning.**
- **Mutable-in-place documents** (type specs, provider definitions, policies, profiles,
  catalog items, consumer manifests): the uuid is frozen; edits bump the version under the
  publish law; each published version's digest is recorded in the pin manifest.
- **Immutable record streams** (`decision_record`, `layer`, `audit_record`, `audit_leaf`,
  `commit_log_entry`, `accreditation`, `regeneration_manifest`, `finding_routing_record`): a
  change is a **new record** — new identity uuid — that names its predecessor via
  `supersedes`; editing or deleting a published record is refused. The layer `ref_uuid`
  machinery survives untouched: an identity pin on an immutable record is already exact.
- The in-repo worked examples of immutable records evolve the same way — the v2-file pattern
  (`registry/instances/example-reference-data-network-zone-v2.yaml` is the standing
  precedent): a revised fixture is a new record with a new uuid superseding the old, whose
  bytes remain in the revision store (git history). Stated here so the first fixture edit
  that the gate refuses is not a surprise.

**6. Accreditation takes the in-toto shape, exact-by-default.** The subject of an attestation
is a stable identity (`subject_uuid`, `capability_uuid` — frozen, per Decision 1); the
attestation records the exact digest(s) it reviewed (`attested_digests`); any validity wider
than those exact bytes (e.g. "this capability across future revisions") is an explicit
declaration, never an implication. Ratified as the default.

**7. Grandfathering: identities freeze in place, history stands.** Every uuid in the tree at
the time of this ruling freezes as-is — including the 18 minted by the 2026-07-25 rotation —
with no re-keying. Prior rotations remain in history as the names of prior revisions; the
changelog rows describing them are never rewritten, only annotated as superseded. The rename
map (`registry/renames.yaml`) keeps its one job: it maps file paths, never identities.

**8. The Reference shape evolves once.** `$defs/Reference` gains its pin fields
(`target_version`, `target_digest`) and the standing-gap `target_authority` field in the same
change, so the canonical reference shape moves a single MINOR instead of two.

## The standards, and what each one settles here

| Standard | The rule it contributes | Realized here as |
|---|---|---|
| Kubernetes object metadata | Three fields, three jobs: `uid` is identity and never changes; `generation` moves on spec change; `resourceVersion` is the change token. One field never does two of these jobs. | uuid = `uid`; version = `generation`; digest = the change token |
| npm registry | Publish law: a published (name, version) is immutable; republishing different bytes under it is refused. | Decision 2; gate rule R2 (republication) |
| OCI distribution | `name@tag` for humans, `name@sha256:…` for proof; the digest lives in a manifest *about* the artifact, never inside it (a self-referential digest is uncomputable). | Decision 3 pin grammar; Decision 4 referrer rule; `registry/pin-manifest.json` |
| git | Immutable content-addressed objects under mutable names; history is the revision store. | The registry's git history remains the revision store; old bytes are always recoverable |
| in-toto / SLSA | An attestation's subject is a name plus the exact digest reviewed; claims bind to bytes, not to labels. | Decision 6; `attested_digests` on the accreditation record |
| RFC 8785 (JCS) | One canonical byte form per JSON document, so equal meaning gives equal hash. | Decision 4; `jcs_bytes()` in the pin-manifest tool |
| RFC 9562 §2.1 | Name-based (v3/v5) uuids are discouraged where collision-resistant content addressing is the actual need — a uuid is an identifier, not an integrity check. | Digests can never be uuids; the exact-bytes job lives in sha256 space, outside identity space |

## Data · Policy · Provider

- **Data (UDLM):** the three fields and their meanings — frozen uuid, published version,
  recorded digest — plus the pin grammar, the family rule, and the manifest/provenance
  carriers. All of it is portable record shape.
- **Policy (DCM):** what to do about distance — pin resolution, debt enumeration, promotion
  on evidence (ADR-046), and whether a profile demands digest pins. The registry records;
  the estate decides.
- **Provider:** providers and capabilities keep frozen identities their accreditations can
  bind to; their *surface* still versions under ADR-045 §8 rules, and the digest of each
  published surface revision is what an attestation cites.

## Consequences

- Accreditation anchors, escrow bindings, and every other identity reference survive edits by
  construction — the collision that triggered this ruling cannot recur, because the rotating
  field no longer exists.
- Exactness is preserved, relocated: what "uuid-precise" pins provided, `@sha256:` pins and
  the (identity, version) publish law now provide, with the industry's own primitives.
- The gate inverts. `tests/check_uuid_rotation.py` (change ⇒ mint a new uuid) becomes
  `tests/check_identity_integrity.py` (change ⇒ keep the uuid, bump the version; immutable
  records supersede, never edit), and `registry/tools/generate_pin_manifest.py --check`
  enforces the publish law across regenerations.
- Two families mean two evolution idioms to know, not one — the cost of no longer pretending
  a ledger entry and a type spec change the same way.
- Follow-ups explicitly out of scope: handle renames as identity events (the manifest keeps
  stranded entries until a declaration mechanism exists), and the DCM-repo alignment wave.
