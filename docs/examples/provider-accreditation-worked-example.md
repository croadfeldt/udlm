# Worked example — declaring a full-stack provider and its sovereignty accreditations

**What this shows:** how one provider declares itself, declares that it manages the **full lifecycle of
VMs, containers, and OpenShift clusters** (and all their constituent capabilities), and how **three
different sovereignty postures** are modelled with the accreditation record — using nothing but the
provider capability declaration (`registry/provider-adopted-standards.schema.json`) and the accreditation
record (`registry/accreditation.schema.json`; `governance/accreditation-and-authorization-matrix.md`).

The scenario:
- **Region sovereignty (US + Canada) for everything** the provider offers — *except* OpenShift.
- **State sovereignty (Minnesota) for containers.**
- **No sovereignty accreditation for OpenShift** at all.

All three artifacts below are live, validated instances — `registry/providers/full-stack-sp.json`,
`registry/instances/accreditation-region-us-ca.yaml`, `registry/instances/accreditation-state-mn.yaml`.

---

## 1. The provider declares itself and its capabilities

A **capability** is the versioned, accreditable unit (`capability_uuid` + `version`); it **contains** the
`(verb × domain)` **categories** it realizes, where topology and sovereignty actually vary (ADR-004 §2).
`full-stack-sp` declares three capabilities:

| Capability (`capability_uuid`, v1.0.0) | Realizes these categories (constituent capabilities) |
|---|---|
| **Virtual Machine Lifecycle** `44e7eb3d…` | `realize_resources/Compute` (Compute.VirtualMachine) · `…/Network` (IPAddress, VirtualNetwork) · `…/Storage` (Volume) |
| **Container Lifecycle** `a26c91c8…` | `realize_resources/Container` (Compute.Container) · `…/Network` · `…/Storage` |
| **OpenShift Cluster Lifecycle** `31aa387c…` | `realize_resources/Compute` (Compute.Cluster) · `…/Network` (VirtualNetwork, Gateway) · `…/Storage` (Volume, Cluster) |

So "full lifecycle of X and all its constituent capabilities" = **one capability that spans the
categories X is built from**. Operational primitives (drain, online-migrate, rolling-update, rehearsal)
are declared per category — e.g. the VM's Compute category advertises `online_migrate` + `drain`.

**The declared sovereignty stance (a *claim*, not yet trust):**
- `provider_defaults.sovereignty = { operating_jurisdictions: [US, CA] }` — the provider's default
  residency stance, inherited by every capability/category that does not override it. So VM, Container,
  **and OpenShift** all *claim* US + CA.
- The Container capability's `realize_resources/Container` category **overrides** it to add Minnesota:
  `{ operating_jurisdictions: [US, CA], data_residency_zones: [us-mn] }` (finest-granularity-wins).

Declaring a stance does **not** make it trusted — that takes a matching accreditation (§3).

**The declaration** (`registry/providers/full-stack-sp.json`, abridged — Network/Storage constituent
categories elided for length; they carry no per-category override and inherit the provider default):

```json
{
  "provider": { "name": "full-stack-sp", "uuid": "ae18b73d-…", "kind": "service" },
  "adopted_standard_support": [
    { "standard": "Redfish",    "supports": ">=1.0",   "direction": "consume" },
    { "standard": "KubeVirt",   "supports": ">=1.0",   "direction": "consume" },
    { "standard": "Kubernetes", "supports": ">=1.28",  "direction": "both" }
  ],
  "provider_defaults": {
    "sovereignty": { "operating_jurisdictions": ["US", "CA"] }
  },
  "capabilities": [
    { "capability_uuid": "44e7eb3d-…", "version": "1.0.0", "name": "Virtual Machine Lifecycle",
      "categories": [
        { "category": "realize_resources/Compute", "resource_types": ["Compute.VirtualMachine"],
          "topology_capability": { "kinds_supported": ["region","zone","host"], "max_separation": "zone" },
          "operational_capability": { "drain": true, "online_migrate": true, "maintenance_mode": true, "rehearsal_support": ["rehearsal"] } },
        { "category": "realize_resources/Network", "resource_types": ["Network.IPAddress","Network.VirtualNetwork"] },
        { "category": "realize_resources/Storage", "resource_types": ["Storage.Volume"] } ] },

    { "capability_uuid": "a26c91c8-…", "version": "1.0.0", "name": "Container Lifecycle",
      "categories": [
        { "category": "realize_resources/Container", "resource_types": ["Compute.Container"],
          "operational_capability": { "drain": true, "rolling_update": true, "online_migrate": true, "rehearsal_support": ["rehearsal"] },
          "sovereignty": { "operating_jurisdictions": ["US","CA"], "data_residency_zones": ["us-mn"] } },
        { "category": "realize_resources/Network", "resource_types": ["Network.IPAddress"] },
        { "category": "realize_resources/Storage", "resource_types": ["Storage.Volume"] } ] },

    { "capability_uuid": "31aa387c-…", "version": "1.0.0", "name": "OpenShift Cluster Lifecycle",
      "categories": [
        { "category": "realize_resources/Compute", "resource_types": ["Compute.Cluster"],
          "operational_capability": { "drain": true, "rolling_update": true, "maintenance_mode": true, "rehearsal_support": ["rehearsal"] } },
        { "category": "realize_resources/Network", "resource_types": ["Network.VirtualNetwork","Network.Gateway"] },
        { "category": "realize_resources/Storage", "resource_types": ["Storage.Volume","Storage.Cluster"] } ] }
  ]
}
```

Note there is **no `sovereignty` block on the OpenShift capability** — it silently inherits the provider
default `{US, CA}`, which is exactly the *claim* §3 shows is untrusted for want of an accreditation.

## 2. Two accreditations attest specific scopes

Trust requires a **1-1 match** between a sovereignty *claim* and an accreditation attesting **exactly**
its scope — **provider × capability × jurisdiction** (§3.3.1). Two accreditation records provide it:

**A — Region (US + CA), everything except OpenShift** (`accreditation-region-us-ca.yaml`):
```yaml
subject_uuid: ae18b73d-…            # full-stack-sp
framework: sovereign
scope:
  capability_scope:
    - capability_uuid: 44e7eb3d-…   # VM Lifecycle      (whole capability, any version — grain 2)
    - capability_uuid: a26c91c8-…   # Container Lifecycle
    # OpenShift (31aa387c-…) intentionally absent
  geographic_scope: [US, CA]
```

**B — State (Minnesota), containers only** (`accreditation-state-mn.yaml`):
```yaml
subject_uuid: ae18b73d-…
framework: sovereign
scope:
  capability_scope:
    - capability_uuid: a26c91c8-…            # Container Lifecycle…
      category: realize_resources/Container  # …narrowed to the container category (grain 2 + category)
  geographic_scope: [US-MN]
```

## 3. What is trusted where — the 1-1 match resolved

For a **sovereign/restricted** placement request, a capability's residency claim is honored only if an
active accreditation matches it on all three axes. Otherwise the claim is `self_asserted` and the
placement is **not** honored (ADR-022):

| Request | Matching accreditation | Trusted for sovereign placement? |
|---|---|---|
| **VM** in US or CA | A (`44e7eb3d` ∈ scope, geo US/CA) | ✅ yes |
| **Container** in US or CA | A (`a26c91c8` ∈ scope, geo US/CA) | ✅ yes |
| **Container** with **Minnesota** residency | B (`a26c91c8`/`…/Container`, geo US-MN) | ✅ yes — the finer state grain |
| **VM** with Minnesota residency | *(none — A is country-grain US/CA, B is containers-only)* | ❌ no |
| **OpenShift** in US or CA | *(none — A omits `31aa387c`)* | ❌ **no — self_asserted** |
| VM/Container in the **EU** | *(none — geo is US/CA only)* | ❌ no |

The two consequences worth stating plainly:
- **OpenShift can still be *provisioned*** — the provider genuinely manages its lifecycle. It just
  **cannot satisfy a sovereign/restricted placement**: with no accreditation covering `31aa387c`, its
  US/CA claim is `self_asserted`. Under a non-sovereign profile (dev/standard) it places normally; under
  sovereign/fsi it is filtered out for any sovereignty-gated request.
- **The region accreditation does not vouch for the state requirement.** A container that must reside in
  Minnesota needs accreditation **B**; **A** (country-grain US/CA) is not a match for `US-MN`. Conversely
  B does not vouch for a VM — its `capability_scope` is the container category only.

## 3a. The gap surfaced — a VM that must reside in Minnesota

A consumer submits a **VM** intent under a **sovereign** profile with a **Minnesota residency**
requirement. DCM resolves placement and runs the 1-1 match for (`full-stack-sp` × VM capability
`44e7eb3d` × `US-MN`):

- Accreditation **A** covers the VM capability — but its `geographic_scope` is country-grain `[US, CA]`,
  which does **not** match `US-MN`.
- Accreditation **B** covers `US-MN` — but its `capability_scope` is the **Container** category only,
  so it does **not** cover the VM capability.

No accreditation matches all three axes, so the VM's Minnesota claim is `self_asserted`. Under a sovereign
profile that is a **hard fail**: the provider is **not eligible** for this request, and — with no other
eligible provider — DCM surfaces an **accreditation gap** (§3.5) instead of silently placing it:

```yaml
accreditation_gap_record:
  uuid: <uuid>
  provider_uuid: ae18b73d-…            # full-stack-sp
  required_framework: sovereign
  required_for: [VM intent requiring US-MN residency]
  gap_type: missing
  detected_at: 2026-07-14T00:00:00Z
  severity: critical
  unmet_capability:
    capability_uuid: 44e7eb3d-…        # VM Lifecycle
    version: null                      # country-grain requirement — no exact version pinned
    category: realize_resources/Compute
  unmet_jurisdiction: [US-MN]
  policy_response: NOTIFY_AND_WAIT      # sovereign-profile default (§3.5)
```

The outcome is **explicit and diagnosable**: the request does not fail with a vague "no capacity" — it
names exactly what is missing (a Minnesota accreditation for the VM capability). The remedy is equally
explicit: `full-stack-sp` obtains a state-MN accreditation whose `capability_scope` includes the VM
capability `44e7eb3d`, and the same request then matches. Contrast the container case, which already has
that accreditation (B) — the *only* difference between "VM in MN → gap" and "Container in MN → honored"
is one accreditation record's `capability_scope`.

That is the point of the per-capability × jurisdiction 1-1 match: a sovereignty shortfall is a **named,
actionable gap at the capability grain**, not an opaque placement failure.

## 4. Lifecycle: what happens when a capability changes

Because each capability carries a `version`, the platform can require the strict binding grain
(§3.3.1 grain 3: `capability_uuid` + `version`) for sovereign/fsi. If `full-stack-sp` changes its
Container capability — new residency zone, new operational primitive, new resource type — it bumps
`a26c91c8` to `1.1.0` and emits `provider.capability_changed`. A grain-3 accreditation bound to `1.0.0`
no longer matches, so the Minnesota claim reverts to `self_asserted` until re-attested. Region/grain-2
bindings (used above) survive the bump. Whether the change expires a binding is the platform's
policy — the dial in §3.3.1.

## Takeaways

- A provider declares its **capabilities** (versioned, accreditable), each spanning the `(verb × domain)`
  **categories** it realizes; sovereignty is claimed per category, finest-wins over the provider default.
- **Claim ≠ trust.** Trust is a 1-1 accreditation match on provider × capability × jurisdiction. No match
  → `self_asserted` → not honored for sovereign placement.
- **Different grains coexist cleanly:** region (country) for VM + Container, state (Minnesota) for
  Containers, nothing for OpenShift — three postures, two accreditation records, one provider.
