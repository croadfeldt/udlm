# Identity — Class-paradigm render (illustrative)

**Illustrative** (the `extends`/Base-Class composition needs the meta-schema change that is part of the paradigm). Identity is the sweep's **cleanest** category — the shared fields are genuinely shared, **no drift, no naming collision** — so it shows the paradigm's happy path *and* the one judgment call it raises: an intermediate sub-grouping.

Sweep result: `handle`, `display_name` shared **3/3** (Group, Person, ServiceAccount); `actor_type`, `authenticated_by`, `credential_ref`, `status` shared **2/3** (Person, ServiceAccount — **not** Group).

---

## `Identity` — Base Class  (`identity.json`)
The universal identity surface every member shares.

```jsonc
{
  "class": "base",
  "resource_type": "Identity",
  "family": "Access",
  "spec": {
    "properties": {
      "handle":       { "type": "string", "description": "Stable unique handle for the identity." },
      "display_name": { "type": "string" },

      // ── actor surface ── shared by Person + ServiceAccount (the authenticatable actors),
      //    NOT by Group (a collection). Lifted here as OPTIONAL — Group leaves them null
      //    ("optional carriers, not mandatory ceremony", entity-types.md). See the judgment note below.
      "actor_type":       { "enum": ["person","service_account"], "description": "Present for actors; absent for Group." },
      "authenticated_by": { "type": "string", "description": "Auth mechanism/provider ref." },
      "credential_ref":   { "$ref": "../data-reference.schema.json#/$defs/data_reference" },
      "status":           { "type": "object", "properties": { "state": { "enum": ["active","suspended","disabled"] } } }
    }
  }
}
```

---

## Type Classes  (extend `Identity`; carry only what's specific)

```jsonc
// identity.person.json
{ "class": "type", "resource_type": "Identity.Person", "extends": "Identity", "family": "Access",
  "spec": { "properties": {
    "email":           { "type": "string" },
    "external_subject":{ "type": "string", "description": "IdP subject (OIDC sub / SAML nameID)." } } } }

// identity.service-account.json
{ "class": "type", "resource_type": "Identity.ServiceAccount", "extends": "Identity", "family": "Access",
  "spec": { "properties": {
    "owner_ref": { "$ref": "../data-reference.schema.json#/$defs/data_reference", "description": "The identity that owns this SA." } } } }

// identity.group.json  — the looser member: a collection, not an actor
{ "class": "type", "resource_type": "Identity.Group", "extends": "Identity", "family": "Access",
  "spec": { "properties": {
    "source":            { "enum": ["local","external"] },
    "external_group_ref":{ "type": "string" },
    "members":           { "type": "array", "items": { "$ref": "../data-reference.schema.json#/$defs/data_reference" } } } } }
```

**Effective wire schema** (ADR-008): e.g. `Identity ⊕ Identity.Person` → `{handle, display_name, actor_type, authenticated_by, credential_ref, status, email, external_subject}`, flattened, closed.

---

## The one judgment call this render surfaces
`handle`/`display_name` are a clean 3/3 Base. The **actor surface** (`actor_type`/`authenticated_by`/`credential_ref`/`status`) is shared by Person + ServiceAccount but *meaningless for Group*. Two honest options — this is exactly the naming-depth test in miniature:

- **(A) Lift to Base as optional** *(rendered above)* — simplest, one level. Cost: Group carries four auth fields it never sets (null). Backed by "optional carriers, not ceremony."
- **(B) Intermediate `Identity.Actor` grouping** — Person + ServiceAccount extend `Identity.Actor` (which holds the auth surface); Group extends `Identity` directly. Cleaner *semantics* (Group has no auth fields at all), at the cost of a fourth level and a `Identity.Actor.Person` name.

Per the naming-depth rule, **(A) wins unless the actor surface grows** — four fields shared by two types don't yet earn a level. If the authenticatable-actor surface expands (sessions, MFA, token policy…), promote to (B). This is the paradigm's judgment working as intended: add the level when the sharing *earns* it, not before.

---

## Identity vs Compute — the two data points
- **Compute (messy):** real drift (`memory` hugepages, `capacity` shapes), a naming collision (`network`), and a same-concept-different-name fork (`vcpu`/`cpu`/`resources.cpu`) the sweep couldn't even see. The paradigm's value = it **fixes** all of these structurally.
- **Identity (clean):** drift-free 3/3 sharing, an obvious Base, and one tidy sub-grouping judgment. The paradigm's value = it **removes duplication** and makes the sharing explicit, with a clear rule for when to add a level.

Between them: the paradigm earns its keep on *both* the messy category (by reconciling) and the clean one (by de-duplicating + guiding), and the applicability test cleanly excludes the no-sharing categories (Facility/Hardware/Security stay flat).
