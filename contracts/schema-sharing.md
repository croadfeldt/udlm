# UDLM — Schema Sharing Protocol Contract

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines how udlm-conformant peers exchange schemas for their entity types,
> events, contracts, and extensions so that any peer can interpret another
> peer's data — even data containing custom types unknown to the receiving
> peer at compile time. This contract is the **mechanism that makes
> wire-compatibility extensible**.

---

## 1. Purpose

Schema-sharing is a **peer-to-peer, machine-to-machine** protocol between
realizations — not a user-facing surface. Consumers use the service catalog and
admins/SREs author types in their own deployment; this contract exists so that
when one realization federates or ingests data carrying a type another peer was
never compiled against, the receiving peer can fetch the sender's schema (from
`/.well-known/udlm/schema-bundle`) and validate it on the fly. It is the
interop layer under the catalog, not a replacement for it.

A peer realization may extend udlm with custom resource types, custom event
types, custom credential types, custom location layers, or other extensions
allowed by the relevant base contract. Wire-compatibility requires that any
other peer can:

- Discover what schemas a remote peer publishes.
- Fetch a remote schema by identifier.
- Validate incoming data against the remote peer's schema.
- Determine version compatibility.

Without schema-sharing, two peers extending udlm independently would diverge
into mutual incompatibility. With it, peers stay interoperable even as they
add domain-specific extensions.

---

## 2. Schema format

A conformant realization MUST publish schemas in **JSON Schema Draft 2020-12**
format. JSON Schema is the normative wire format for:

- Entity type definitions
- Event payload schemas
- Provider contract extensions
- Policy contract extensions
- Credential type extensions
- Location layer type extensions
- Custom error code `details` field schemas
- Any other udlm-extensible artifact

JSON Schema is chosen for: maturity, broad tooling support, ability to express
references between schemas, declarative validation semantics, machine readability.

A realization MAY translate JSON Schemas to other formats internally (e.g., for
storage or runtime validation). The **wire format** between peers is always
JSON Schema 2020-12.

---

## 3. Schema bundle

A peer publishes its schemas as a **schema bundle**: a versioned collection
that catalogs all its declared types and extensions.

### Bundle structure

```json
{
  "bundle_uuid": "f3b64dda-...",
  "bundle_version": "2.4.1",
  "realization": {
    "name": "DCM",
    "vendor": "example-org",
    "udlm_version": "0.1.0"
  },
  "published_at": "2026-05-26T14:32:18.456Z",
  "manifest": {
    "entity_types": [
      { "id": "vm.standard", "version": "1.2.0", "schema_url": "/schemas/entity_types/vm.standard/1.2.0" },
      { "id": "ip.allocation", "version": "1.0.0", "schema_url": "/schemas/entity_types/ip.allocation/1.0.0" }
    ],
    "event_types": [
      { "id": "request.scheduled", "version": "1.0.0", "schema_url": "/schemas/event_types/request.scheduled/1.0.0" }
    ],
    "credential_types": [],
    "location_layer_types": [
      { "id": "edge_pod", "version": "1.0.0", "schema_url": "/schemas/location_layers/edge_pod/1.0.0" }
    ],
    "policy_extensions": [],
    "error_extensions": [
      { "id": "auth.token_replay_detected", "version": "1.0.0", "schema_url": "/schemas/errors/auth.token_replay_detected/1.0.0" }
    ]
  }
}
```

| Field | Description |
|---|---|
| `bundle_uuid` | UUID identifying this bundle release |
| `bundle_version` | Semver for the bundle as a whole |
| `realization` | Self-description of the publishing peer |
| `realization.udlm_version` | Which udlm version this bundle conforms to |
| `published_at` | RFC 3339 UTC timestamp |
| `manifest` | Categorized list of all schemas in the bundle, with per-schema versions |

A peer MUST be able to publish its bundle and to fetch a remote peer's bundle.

---

## 4. Standardized endpoints

Conformant realizations expose schema-sharing at well-known paths:

| Endpoint | Returns |
|---|---|
| `GET /.well-known/udlm/schema-bundle` | Latest schema bundle for this realization |
| `GET /.well-known/udlm/schema-bundle?version=2.4.1` | Specific bundle version |
| `GET /schemas/{category}/{id}/{version}` | Individual schema by category, id, version |
| `GET /schemas/{category}/{id}/versions` | All available versions of a schema |
| `GET /.well-known/udlm/conformance` | Conformance declaration (see [`CONFORMANCE.md`](../CONFORMANCE.md)) |

These endpoints MUST be accessible to authenticated peers per the realization's
federation auth contract. They MAY be public-readable at the realization's
discretion.

Non-HTTP transports (gRPC, message bus) MUST provide equivalent operations
documented in the realization's conformance declaration.

---

## 5. Version negotiation

When two peers interact, they negotiate compatible schema versions:

1. Each peer fetches the other's schema bundle.
2. For each shared artifact (entity type, event type, etc.), the peers
   identify the highest mutually-supported version per semver.
3. Communication uses the negotiated version. The version is included in the
   wire envelope for the artifact.
4. If no compatible version exists for a required artifact, the interaction
   fails with `schema.version_incompatible`.

### Semver rules

- **Patch** (1.2.3 → 1.2.4): backward-compatible additions to optional fields,
  documentation changes, examples. No wire breakage.
- **Minor** (1.2.0 → 1.3.0): backward-compatible additions including new
  optional fields, new error codes within existing namespaces.
- **Major** (1.x → 2.x): backward-incompatible changes. Peers running 1.x
  cannot interoperate with peers running 2.x on the changed artifact unless
  they implement multi-version support.

A peer MAY support multiple major versions of an artifact simultaneously by
publishing each version in the bundle.

---

## 6. Schema discovery for unknown data

When a peer receives data containing an unknown type, it MUST:

1. Identify the source peer (from the data's provenance or transport metadata).
2. Fetch the source peer's schema bundle (or use cached version).
3. Locate the schema for the unknown type.
4. Validate the data against the schema.
5. If the schema is unavailable or validation fails:
   - For required fields: reject with `schema.unknown_type`.
   - For optional fields: log and drop the field, surface the missing context
     to the consumer in an advisory header.

This is the mechanism that allows a peer to consume data with custom types it
has never seen before — it learns the schema on demand.

---

## 7. Schema caching and freshness

To avoid round-trips on every interaction:

- Peers MAY cache remote schema bundles.
- Cached bundles MUST be revalidated when the source peer publishes a new
  bundle version (via federation event `schema.bundle_updated`, see
  [`event-catalog.md`](event-catalog.md)).
- The bundle endpoint MUST honor HTTP caching headers (ETag, If-None-Match)
  for HTTP transports.
- Per-schema URLs MUST be immutable for a given `(id, version)` tuple.

---

## 8. Conformance declaration

Beyond schema bundles, every conformant realization publishes a **conformance
declaration** at `/.well-known/udlm/conformance` describing:

- Which udlm version it conforms to.
- Which optional capabilities it implements.
- Which interop surfaces it exposes.
- Auth requirements for accessing its schemas.
- Bundle version available.

See [`CONFORMANCE.md`](../CONFORMANCE.md) for the conformance declaration
schema and validation requirements.

---

## 9. Schema authoring rules

A schema in a published bundle MUST:

- Use JSON Schema Draft 2020-12.
- Declare `$id` matching its `schema_url` in the bundle manifest.
- Declare `$schema` (the meta-schema URL).
- Be self-contained or reference only other schemas in the same bundle or in
  the udlm core schemas.
- NOT reference internal-only schemas (those scoped to the realization).

A schema MAY:

- Reference udlm core schemas via fully-qualified URLs.
- Include human-readable documentation in `title` / `description`.
- Declare `examples` for tooling support.

---

## 10. Core udlm schemas

The udlm specification publishes a baseline set of schemas at canonical URLs
(to be hosted alongside the udlm repo). Every realization's bundle implicitly
depends on these. The baseline includes:

- Error envelope schema
- Event envelope schema
- Identifier schema (UUID, handle, reference forms)
- Timestamp schema (RFC 3339 UTC ms-precision)
- Provider contract base
- Policy contract base
- Rate limit declaration schema
- Bundle manifest schema (this document's bundle structure, recursively)

These are the **shared vocabulary** every peer can assume.

---

## 11. Validation rules (conformance checks)

A conformant realization MUST:

- Publish a schema bundle at `/.well-known/udlm/schema-bundle`.
- Publish individual schemas at the URLs declared in the bundle manifest.
- Use JSON Schema Draft 2020-12 for all schemas.
- Honor semver for schema versioning.
- Reject incompatible-version interactions with `schema.version_incompatible`.
- Reject unknown-type data with `schema.unknown_type` (where required fields)
  or downgrade gracefully (optional fields).
- Cache remote bundles correctly and revalidate on update notifications.

---

## 12. Related contracts

- [`identifier-scheme.md`](identifier-scheme.md) — UUIDs and references in bundles
- [`time-and-clock.md`](time-and-clock.md) — `published_at` timestamps
- [`error-model.md`](error-model.md) — `schema.*` error codes
- [`event-catalog.md`](event-catalog.md) — `schema.bundle_updated` federation event
- [`layering-and-versioning.md`](../foundations/layering-and-versioning.md) — semver conventions
- [`capability-discovery.md`](capability-discovery.md) — broader capability declaration mechanism
- [`provider-contract.md`](provider-contract.md) — provider schemas in the bundle
- [`policy-contract.md`](policy-contract.md) — policy schemas in the bundle
- [`CONFORMANCE.md`](../CONFORMANCE.md) — conformance declaration that complements the bundle
