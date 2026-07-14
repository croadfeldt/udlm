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
