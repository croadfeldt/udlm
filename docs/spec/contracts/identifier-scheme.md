# UDLM — Identifier Scheme Contract

**Established:** 2026-05-26
**Maps to:** DATA

> Defines how entities, requests, policies, events, and other first-class
> artifacts are identified, scoped, and referenced across a udlm-conformant
> implementation and between peers. Wire-compatible: any conformant peer MUST
> produce identifiers that any other conformant peer can deserialize, scope-resolve,
> and reference.

---

## 1. Purpose

A peer implementation that consumes data emitted by another peer must be able to:

- Recognize what kind of thing an identifier refers to.
- Determine the identifier's scope (global vs tenant vs implementation).
- Decide whether the identifier is portable across implementations or local-only.
- Resolve cross-references between artifacts without prior knowledge of the
  emitting system's internals.

*Worked example.* Peer A emits a VM entity that references a `Network.VirtualNetwork` by handle. Peer B,
receiving it, must recognize the reference *kind* (a network), determine its *scope* (a global, portable
handle — not A's implementation-local uuid), resolve it to B's own copy of that network, and reject it if the
scope doesn't match — all without knowing A's internals. The rules below make that mechanical.

This document defines the rules every conformant implementation MUST follow when
generating, formatting, scoping, and referencing identifiers.

---

## 2. Identifier types

A conformant implementation MUST distinguish three identifier types:

| Type | Form | Scope | Mutability | Portable across peers |
|---|---|---|---|---|
| **UUID** | RFC 9562 stringified | Globally unique | Immutable | Yes |
| **Handle** | namespaced string | Tenant- or realm-scoped | Mutable (with audit) | No — must be rebound on import |
| **Reference** | typed cross-doc pointer | Inherits target's scope | Tracks target | Yes if target is portable |

### 2.1 UUID — THE identifier standard (normative)

UDLM/DCM standardize on **RFC 9562** (Universally Unique IDentifiers, May 2024 — obsoletes its
2005 predecessor; all earlier-era formats remain valid under 9562, which additionally defines
v6/v7/v8). Every UUID citation in this spec is RFC 9562.

- **Format**: RFC 9562 §4 canonical textual form — lowercase, hyphenated, no braces, no `urn:`
  prefix. Example: `f3b64dda-2c95-4a1b-8d3e-7a9c1b2e4f8d`.
- **Version policy (closed — not extensible):**

  | Version | Status | Use | Why |
  |---|---|---|---|
  | **v4** | **REQUIRED** | entity/artifact IDENTITY (resources, types, policies, providers, requests) | unpredictable (CSPRNG), leaks nothing, collision-safe across independent implementations; the Kubernetes-uid pattern |
  | **v7** | **REQUIRED** | TIME-ORDERED artifacts only (audit-chain leaves, event ids) — declared in the field schema | millisecond-ordered → index locality + total order for the audit chain |
  | v1/v6 | PROHIBITED | — | embed MAC/timestamp (information leak); ordering need is served by v7 |
  | v3/v5 | PROHIBITED | — | name-derived/deterministic: two implementations hashing the same name mint the SAME uuid — violates the identity-is-minted-once model and §5 no-reassignment |
  | v8 | PROHIBITED | — | vendor-defined layout: not interoperable across peers |

- **Generation**: v4 from a cryptographically secure RNG (the platform's standard source —
  `uuidgen`, `uuid.uuid4()`, `crypto.randomUUID()`); v7 per RFC 9562 §5.7.
- **Validation**: peers MUST reject at ingest any malformed UUID and any version outside
  {v4, v7-where-declared} — checking BOTH the version nibble and the variant bits
  (`^[0-9a-f]{8}-[0-9a-f]{4}-[47][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, version per field).
- **Uniqueness**: globally unique across all implementations. Collision probability is assumed zero
  for v4; v7 collisions handled by the audit-chain ordering rule.

### 2.2 Handle

- **Format**: `[namespace/]name` where `name` matches `[a-z0-9][a-z0-9-]{0,61}[a-z0-9]` and `namespace` follows the same pattern with `/` separators allowed.
- **Scope**: tenant-scoped by default; implementation-scoped if explicitly declared.
- **Mutability**: handles MAY change. Every change MUST be audited (old handle, new handle, timestamp, actor).
- **Portability**: handles are NOT portable across peers. On import from another peer, a handle MUST be rebound (the target keeps its UUID; the importing peer assigns its own handle if needed).
- **Resolution**: a handle resolves to exactly one UUID within its scope. Reverse resolution (UUID → current handle) is always available.

### 2.3 Reference

A reference is a typed pointer to another artifact. Wire format:

```json
{
  "ref_type": "entity" | "request" | "policy" | "event" | "credential" | ...,
  "uuid": "f3b64dda-...",
  "handle": "tenant-a/web-tier-vm",   // optional, advisory only
  "version": "1.2.0"                   // optional, target version
}
```

- `uuid` is REQUIRED and authoritative.
- `handle` is OPTIONAL and advisory — peers MUST NOT rely on it for resolution.
- `version`, if present, refers to the target's content version (see versioning rules in `layering-and-versioning.md`).

---

## 3. Scope rules

Every identifier carries an implicit scope. A conformant implementation MUST be
able to express and honor these scopes:

| Scope | Holders | Cross-scope resolution |
|---|---|---|
| **Global** | UUIDs | Always resolvable across peers |
| **Implementation** | Internal-only handles, internal credentials | NOT exported to peers; opaque outside |
| **Tenant** | Tenant-scoped handles, tenant artifacts | Resolved within the tenant; cross-tenant requires explicit authorization |
| **Request-local** | Field-injection bindings within a request group | Exists only for the lifetime of the request |

A peer MUST refuse to resolve a scope it does not recognize, returning the
error `validation.scope_not_recognized` (see [`error-model.md`](error-model.md)).

---

## 4. Portability rules

When a peer imports data from another peer (federation, brownfield ingestion,
peering):

1. **UUIDs are preserved.** The importing peer MUST NOT regenerate UUIDs for
   imported artifacts. If a UUID collision is detected with a local artifact,
   the import MUST fail with `validation.uuid_collision`.
2. **Handles are rebound.** Imported handles MAY conflict with local namespace
   conventions; the importing peer assigns its own handle while preserving the
   UUID.
3. **References are preserved by UUID.** Reference handles MAY be re-rendered
   to match the importing peer's bindings, but the underlying UUID is canonical.
4. **Internal-scope identifiers MUST NOT be exported.** A peer that exports
   data MUST omit fields scoped to its own implementation.

---

## 5. Identifier reassignment

Some operational scenarios reassign an artifact's owner or scope:

- **Tenant migration**: an entity moves from tenant A to tenant B. The
  `entity_uuid` is preserved. The tenant-scoped handle MAY change. An audit
  record MUST be written.
- **Implementation migration** (rare): an artifact moves between peer implementations.
  The UUID is preserved. The new implementation treats it as imported (rule 4 above).
- **Decommissioning**: an artifact transitions to a terminal lifecycle state.
  Its UUID remains valid for historical resolution; the handle MAY be released
  for reuse after the retention period defined in the audit policy.

UUIDs MUST NEVER be reassigned to a different artifact. Reuse is a contract
violation and MUST be detected and rejected by conformant peers.

---

## 6. Wire format

When serialized for transport between peers:

- UUIDs as lowercase hyphenated strings (no braces, no URN prefix).
- Handles as plain strings.
- References as JSON objects per section 2.3.
- All identifier fields appear in the artifact's declared schema (see
  [`schema-sharing.md`](schema-sharing.md)).

---

## 7. Validation rules (conformance checks)

A conformant implementation MUST:

- Reject malformed UUIDs at ingest.
- Reject handles violating the format pattern.
- Reject references missing the `uuid` field.
- Reject identifier reassignment attempts.
- Audit every handle change.
- Refuse to export internal-scope identifiers.

A test suite for these rules is part of the conformance specification
([`CONFORMANCE.md`](../../../CONFORMANCE.md)).

---

## 8. Related contracts

- [`time-and-clock.md`](time-and-clock.md) — timestamps embedded in identifiers (UUIDv7)
- **RFC 9562** (https://www.rfc-editor.org/rfc/rfc9562) — the adopted UUID standard (IETF Trust, compatible-reference)
- [`schema-sharing.md`](schema-sharing.md) — how peers exchange the type definitions identifiers point to
- [`error-model.md`](error-model.md) — error codes raised on identifier violations
- [`event-catalog.md`](event-catalog.md) — identifiers used in event envelopes
- [`provider-contract.md`](provider-contract.md) — provider identifier declaration

---

## 9. The reference/filter URL (URF)

**What this settles.** One URL grammar for every way the system points at data — type and
instance references, version/digest pins, filters, stored criteria, layer targeting, and
field projection — and the `URF-*` rules that govern it. Two conformance tests define the
mechanism:

1. **Dereference** — every well-formed URF resolves to its target data via the resolution
   contract (§9.6). UDLM owns the denotation; serving it is implementation (ADR-008 — the
   UDLM/DCM boundary test).
2. **Portability** — a filter moves **verbatim** between a live query, a stored criterion,
   layer targeting, and a tool argument, meaning the same set everywhere. Re-expressing a
   filter to move it between surfaces is nonconformant.

Design invariant: **one canonical string form; any number of one-way projections** (the
block form §9.4, JSON embedding, English renderings) — never a second parse surface.

### 9.1 Grammar — five axes

```
[//authority/]path[@pin][?query][#fragment]
```

| Axis | Delimiter | Carries | Values |
|---|---|---|---|
| authority | `//` | whose namespace; elided = local | dotted authority (ADR-038 §10; peer roots per ADR-040) |
| path | `/` | WHAT | `Category/Type[/Provider]` (registry space) · `estate/<handle>` (instance space) · `uuid/<v4>` (resolved form) |
| pin | `@` | WHICH version/bytes | `@MAJOR.MINOR.REVISION` or `@sha256:<hex>` — ADR-051's grammar, carried verbatim |
| query | `?` | WHICH ONES | one RSQL expression (§9.2) + operational terms (§9.3) |
| fragment | `#` | WHICH FIELD | dot-path element/field projection |

- **A reference is a filter constrained to cardinality 1.** A URF used where one thing is
  required must resolve uniquely; more than one match refuses `ambiguous` with
  `candidate_targets` (service-dependencies §15's UnmetDependency vocabulary).
- **Authored by handle, resolved to uuid — both ends one grammar** (AEP-124 unchanged):
  `estate/jobs/nightly-backup` resolves to `uuid/4c1f8e2a-…@sha256:…`; a sealed citation is
  itself a valid URF.
- **Names are not paths.** Dotted PascalCase (`Compute.VM`) is the type NAME and appears in
  *values* (`resource_type==Compute.VM`); the slash form is the *path* spelling of the same
  identity (`Compute/VM` — lossless bijection, since name segments never contain dots).
  Casing separates the two dot notations: `PascalCase.Dotted` = name, `snake_case.dotted` =
  field path. Selector dots address **within one record only** — crossing an edge is never
  a dot (virtual fields §9.2 are the sanctioned bridge).
- **The class address is the URF registry subset.** ADR-038 §10's coordinate
  (`https://udlm.dev/class/Compute/VM#cpu`) IS a URF; `registry/tools/resolve_class_address.py`
  is the registry half of the URF resolver.

### 9.2 The query axis — uniform RSQL

The query is **one RSQL expression**. The accepted subset — exactly this, never "RSQL" by
name alone:

- Comparators: `==` `!=` `=gt=` `=ge=` `=lt=` `=le=` `=in=` `=out=`
- AND: `;` (canonical) — `&` accepted on input, canonicalized to `;`
- OR: `,` · Grouping: `( )`
- Selectors: dot-path field addresses (`cpu.count`, `labels.concern`, `status.state`)
- Values: bare when URL-unreserved; single-quoted otherwise (`'a b'`) — `'` is URL-legal
  unencoded; `"` is not accepted
- Wildcard: `*` inside `==`/`!=` values = glob, zero-or-more (the FIQL-native wildcard;
  URL-legal). Not valid inside `=in=`/`=out=` members. Quoting makes it literal
  (`name=='a*b'`). Canonicalization treats it as an ordinary character.
- Placeholders: RFC 6570 level-1 templates; the one blessed variable is `{self}` (the
  record carrying the expression) — literal in canonical form, substituted at resolution.

**Virtual fields** (closed set; each is a derived predicate, never stored data):

- `member_of` — membership in a named grouping: `member_of==access/groupings/hold`,
  `member_of!=…` (exclusion), `member_of=in=(g1,g2)` (either). Criterion→criterion
  references form a dependency graph; **cycles refuse** (the CYCLE discipline applied to
  criteria).

Examples:

```
estate?resource_type==Compute.VM;tenant_uuid==abc;zone!=b
estate?resource_type==Compute.*                       # glob over the name
estate?uuid=in=(89d02cc3-…,4c1f8e2a-…)                # explicit set (the marked exception)
estate?tenant_uuid==abc;member_of!=access/groupings/maintenance-hold
Compute/VM@1.2.0#cpu                                  # pinned element projection
//state.mn/Compute/VM#firmware                        # federated authority
```

### 9.3 The operational layer — single `=` at dereference only

Denotational terms always use `==`/`!=`/`=op=`; **single `=` is reserved for operational
terms** — the lexical discriminator makes `estate?tenant_uuid==abc&page_size=50`
unambiguous. Reserved operational names: `page_size`, `page_token`, `order_by`, `fields`,
`view` (the AEP-132/158 vocabulary). Operational terms are legal **only at a live
dereference**: canonicalization strips them, and a stored form (criterion, covers, citation)
containing one is refused. Selectors may not collide with reserved operational names.

### 9.4 Block form — the URL split at its own delimiters

Authoring ergonomics for YAML: axis keys whose values are **verbatim URF substrings**;
query items are verbatim RSQL terms joined with `;`. Assembly is concatenation with each
axis's delimiter; splitting is the inverse. One parser validates both forms (block → join →
parse). A native YAML/JSON *map* form is *rejected* — it would be a second parse surface.

```yaml
criterion: "estate?tenant_uuid=={self};resource_type==Compute.VM"   # canonical
criterion:                                                          # SAME value
  path: estate
  query:
    - tenant_uuid=={self}
    - resource_type==Compute.VM
```

### 9.5 Canonical form

Identity, comparison, and digests are computed **only over the assembled canonical
string**. Canonicalization: RFC 3986 syntax normalization · `&` → `;` · operands of the
same operator sorted bytewise, recursively (`b;a` ≡ `a;b`) · operational terms stripped ·
minimal percent-encoding, uppercase hex · single-quote quoting · `{self}` literal ·
dotted-name path input rewritten to slash form. The characters `@ ? #` are **reserved** —
illegal in handles and name segments (naming-conventions §6).

Two transport rules: a URF longer than a practical URL limit is carried as the block form
in a request body — same canonical identity, not a second mechanism. **Credentials never
appear in a URF**: auth is transport-layer; a token in the query would leak into logs,
seals, and digests.

### 9.6 Resolution contract

| URF shape | Resolves to |
|---|---|
| `Category/Type` | the served type spec |
| `Category/Type@pin#element` | that version's element definition |
| `estate/<handle>` | the one instance record (cardinality 1) |
| `estate?…` | the matching record set |
| `…#field` | the field projection of a **cardinality-1** resolution |
| `//peer/…` | the same, resolved by that authority |

`#` on a set resolution is **deferred** — refused at this revision; per-member projection
(columnar reports) is a named future extension requiring its own ruling. Every dereference
is a boundary crossing: the governance matrix evaluates the read, `#` projections cross the
policy information firewall (ADR-041), and refusals follow error-model §3.3's
existence-disclosure rule (not-found ≡ not-authorized).

### 9.7 Stored criteria

A stored URF (an `Access.Grouping` criterion, layer targeting, any persisted filter)
filters **declared fields only** — identity-stable data (`tenant_uuid`, ownership, labels,
type). Operational state (`run_state`, drift, staleness) composes at query time and never
appears inside a stored criterion.

### 9.8 What URF replaces — and deliberately does not

**Replaces** (each removed in the PR that lands its URF form — no parallel mechanisms):
the ADR-038 §10 class-address as a separate grammar (subsumed here), the ADR-054 `covers`
selector grammar, the structured `Reference`/`data_reference` object serializations, the
policy match-condition array, and grouping member semantics. **Deliberately does not
replace:** graph diagnostics (blast radius, reachability — edge traversal is never in the
filter grammar; `member_of` is the one sanctioned bridge), the ADR-041 firewall (URF is the
*addressing*; PROJ is the *policy* at the address), and the pin grammar (ADR-051, carried
verbatim, not duplicated).

### 9.9 Rules

| Rule | Statement |
|---|---|
| `URF-001` | A URF field (`format: udlm-ref-url` / `udlm-filter-url`) MUST parse under §9.1–§9.2's grammar; a malformed URF is refused at validation, never coerced. |
| `URF-002` | Identity, equality, and digests over a URF are computed ONLY over its canonical form (§9.5); two spellings with one canonical form are one identity. |
| `URF-003` | `@`, `?`, `#` are reserved: illegal in handles and name segments. |
| `URF-004` | A URF used as a reference (cardinality 1) that resolves to more than one target is refused `ambiguous` with `candidate_targets`; it is never silently narrowed. |
| `URF-005` | A stored URF filters declared fields only; a stored form containing an operational term (single `=`) or operational-state selector is refused. |
| `URF-006` | Criterion→criterion references (`member_of` and future virtual fields) MUST be acyclic; a cycle is refused at validation. |
| `URF-007` | Credentials or bearer material MUST NOT appear in any URF axis. |
