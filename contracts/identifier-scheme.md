# UDLM — Identifier Scheme Contract

**Document Status:** ✅ Complete — Normative (UUID standard ratified 2026-07-04)
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines how entities, requests, policies, events, and other first-class
> artifacts are identified, scoped, and referenced across a udlm-conformant
> realization and between peers. Wire-compatible: any conformant peer MUST
> produce identifiers that any other conformant peer can deserialize, scope-resolve,
> and reference.

---

## 1. Purpose

A peer realization that consumes data emitted by another peer must be able to:

- Recognize what kind of thing an identifier refers to.
- Determine the identifier's scope (global vs tenant vs realization).
- Decide whether the identifier is portable across realizations or local-only.
- Resolve cross-references between artifacts without prior knowledge of the
  emitting system's internals.

This document defines the rules every conformant realization MUST follow when
generating, formatting, scoping, and referencing identifiers.

---

## 2. Identifier types

A conformant realization MUST distinguish three identifier types:

| Type | Form | Scope | Mutability | Portable across peers |
|---|---|---|---|---|
| **UUID** | RFC 4122 stringified | Globally unique | Immutable | Yes |
| **Handle** | namespaced string | Tenant- or realm-scoped | Mutable (with audit) | No — must be rebound on import |
| **Reference** | typed cross-doc pointer | Inherits target's scope | Tracks target | Yes if target is portable |

### 2.1 UUID — THE identifier standard (normative)

UDLM/DCM standardize on **RFC 9562** (Universally Unique IDentifiers, May 2024 — obsoletes
RFC 4122; all 4122-era formats remain valid under 9562, which additionally defines v6/v7/v8).
Citations of "RFC 4122" elsewhere in this spec read as RFC 9562.

- **Format**: RFC 9562 §4 canonical textual form — lowercase, hyphenated, no braces, no `urn:`
  prefix. Example: `f3b64dda-2c95-4a1b-8d3e-7a9c1b2e4f8d`.
- **Version policy (closed — not extensible):**

  | Version | Status | Use | Why |
  |---|---|---|---|
  | **v4** | **REQUIRED** | entity/artifact IDENTITY (resources, types, policies, providers, requests) | unpredictable (CSPRNG), leaks nothing, collision-safe across independent realizations; the Kubernetes-uid pattern |
  | **v7** | **REQUIRED** | TIME-ORDERED artifacts only (audit-chain leaves, event ids) — declared in the field schema | millisecond-ordered → index locality + total order for the audit chain |
  | v1/v6 | PROHIBITED | — | embed MAC/timestamp (information leak); ordering need is served by v7 |
  | v3/v5 | PROHIBITED | — | name-derived/deterministic: two realizations hashing the same name mint the SAME uuid — violates the identity-is-minted-once model and §5 no-reassignment |
  | v8 | PROHIBITED | — | vendor-defined layout: not interoperable across peers |

- **Generation**: v4 from a cryptographically secure RNG (the platform's standard source —
  `uuidgen`, `uuid.uuid4()`, `crypto.randomUUID()`); v7 per RFC 9562 §5.7.
- **Validation**: peers MUST reject at ingest any malformed UUID and any version outside
  {v4, v7-where-declared} — checking BOTH the version nibble and the variant bits
  (`^[0-9a-f]{8}-[0-9a-f]{4}-[47][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, version per field).
- **Uniqueness**: globally unique across all realizations. Collision probability is assumed zero
  for v4; v7 collisions handled by the audit-chain ordering rule.

### 2.2 Handle

- **Format**: `[namespace/]name` where `name` matches `[a-z0-9][a-z0-9-]{0,61}[a-z0-9]` and `namespace` follows the same pattern with `/` separators allowed.
- **Scope**: tenant-scoped by default; realization-scoped if explicitly declared.
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

Every identifier carries an implicit scope. A conformant realization MUST be
able to express and honor these scopes:

| Scope | Holders | Cross-scope resolution |
|---|---|---|
| **Global** | UUIDs | Always resolvable across peers |
| **Realization** | Internal-only handles, internal credentials | NOT exported to peers; opaque outside |
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
   data MUST omit fields scoped to its own realization.

---

## 5. Identifier reassignment

Some operational scenarios reassign an artifact's owner or scope:

- **Tenant migration**: an entity moves from tenant A to tenant B. The
  `entity_uuid` is preserved. The tenant-scoped handle MAY change. An audit
  record MUST be written.
- **Realization migration** (rare): an artifact moves between peer realizations.
  The UUID is preserved. The new realization treats it as imported (rule 4 above).
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

A conformant realization MUST:

- Reject malformed UUIDs at ingest.
- Reject handles violating the format pattern.
- Reject references missing the `uuid` field.
- Reject identifier reassignment attempts.
- Audit every handle change.
- Refuse to export internal-scope identifiers.

A test suite for these rules is part of the conformance specification
([`CONFORMANCE.md`](../CONFORMANCE.md)).

---

## 8. Related contracts

- [`time-and-clock.md`](time-and-clock.md) — timestamps embedded in identifiers (UUIDv7)
- **RFC 9562** (https://www.rfc-editor.org/rfc/rfc9562) — the adopted UUID standard (IETF Trust, compatible-reference)
- [`schema-sharing.md`](schema-sharing.md) — how peers exchange the type definitions identifiers point to
- [`error-model.md`](error-model.md) — error codes raised on identifier violations
- [`event-catalog.md`](event-catalog.md) — identifiers used in event envelopes
- [`provider-contract.md`](provider-contract.md) — provider identifier declaration
