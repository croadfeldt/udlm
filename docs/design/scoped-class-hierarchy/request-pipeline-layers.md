# Data layers in a request pipeline — worked example

Two *kinds* of layer, and this example shows both doing their distinct jobs on one `Compute.VM` request:
- **Assembly layers** (`base → core → intermediate → service → request`, then `policy` over the result) — build the resource's **own effective spec** by contributing/overriding field values. Higher class overrides lower **field-by-field**; a `narrow_only` layer may only **tighten**, never loosen (E1).
- **`reference_data` layers** — orthogonal bundles the resource **references** (dual-anchor), resolved separately, **never merged in** (the references-context axis).

Each assembly layer's `fields` are dot-path values, and **each records its own uuid as that field's provenance**.

---

## The assembly stack (lowest authority first)

```yaml
# Each layer declares `covers` — a §10 selector list (authority + Category.Type.Provider + attribute
# predicates, wildcarded). DCM GATHERS every layer whose `covers` matches this VM, then orders by precedence.

# 1. base — foundation defaults (every chain begins here)
layer_type: base
covers: [ Compute.* ]                     # foundation for the whole Compute category
fields:
  cpu.count: 2
  memory.size: 4Gi
  run_state.desired_state: running

# 2. core — standards / compliance (constraint: tightens only)
layer_type: core
narrow_only: true
covers: [ Compute.*, Storage.* ]          # org-wide encryption/compliance standard
fields:
  storage.encryption: true              # required; lower layers cannot loosen it
  guest_os: {narrow the eligible os_image REFERENCES → FIPS-validated set}   # constrains WHICH os_image entities may be referenced

# 3. intermediate — org customization
layer_type: intermediate
covers: [ Compute.VM.*, Storage.* ]       # org defaults for VMs + storage
fields:
  labels.cost_center: {required}
  storage.tier: gold                    # org default
  placement.zone: dc-east-1             # org default
  guest_os: {narrow the os_image references further → org-approved}   # within core's FIPS set

# 4. service — the "web-tier VM" catalog-item defaults
layer_type: service
covers: [ Compute.VM.* ]                  # the web-tier profile applies to VMs
fields:
  cpu.count: 4
  memory.size: 16Gi
  networks[0].app_profile_ref: {data_reference → platform/app-profiles/web-tier}   # a references-context, not a value

# 5. request — the consumer's actual request (targets THIS instance; no covers selector — it IS the request)
layer_type: request
fields:
  cpu.count: 8
  memory.size: 32Gi
  guest_os: {reference_data_type: os_image, named_head: os-images.rhel-9}   # a REFERENCE to a named os_image entity (not a bare string); the ref must be ∈ (core FIPS ∩ intermediate approved)
  labels.cost_center: eng-1234

# 6. policy — applied OVER the assembled result (fill / validate / gate)
layer_type: policy
covers: [ peer.dcm.east/Compute.VM.* ]    # placement + sovereignty policy for VMs in this authority
fields:
  placement.zone: {policy confirms or re-places by live capacity}
  # + sovereignty gate validates residency; size-limit policy asserts cpu.count ≤ org max
```

---

## Effective assembled spec  (higher overrides lower, field-by-field; provenance in brackets)

```jsonc
{
  "cpu":      { "count": 8 },                         // [request]  (over service 4, over base 2)
  "memory":   { "size": "32Gi" },                     // [request]
  "storage":  { "encryption": true, "tier": "gold" }, // encryption [core, narrow_only — unloosenable] · tier [intermediate]
  "guest_os": { "reference_data_type": "os_image", "named_head": "os-images.rhel-9" },  // [request] — a data_reference (not a string), validated ∈ core∩intermediate
  "run_state":{ "desired_state": "running" },         // [base]
  "labels":   { "cost_center": "eng-1234" },          // [request] satisfies [intermediate]'s required marker
  "placement":{ "zone": "dc-east-2" },                // [policy] (re-placed by capacity, over [intermediate] default)
  "networks": [ { "app_profile_ref": "…" } ]          // [service] — a REFERENCE, resolved separately (below)
}
```
Every value traces to the layer that set it — the audit trail is the pipeline. `narrow_only` is why `storage.encryption` can't be turned off downstream: core tightened it, and nothing may loosen.

---

## References-context attached (NOT assembled in) — dual anchor

The resource *points at* two orthogonal bundles; their data is **not** copied into the spec:

```yaml
app_profile:                              # web-tier bundle (explicitly referenced by the service layer)
  immutable_anchor: {ref_uuid: a99c…}     # pinned: the web-tier profile AS IT WAS at request time (reproducible/audit)
  named_head:       platform.app-profiles.web-tier    # current binding (dotted; a field is platform.app-profiles.web-tier#zone)
  reference_data_type: app_profile

data_center:                              # DC-info bundle (AUTO-attached by coverage — no explicit ref needed)
  covers:           [ peer.dcm.east/Compute.*, "*[.residency = dc-east]" ]   # every resource in dc-east
  immutable_anchor: {ref_uuid: dc17…}     # pinned: dc-east state at placement
  named_head:       facility.dc.dc-east   # current: live dc-east info
  reference_data_type: data_center
```
Resolve the **pin** for reproducibility ("what the profile/DC was when this VM was placed"), the **named head** for currency ("the current web-tier profile / current DC state"), or both. Cross-boundary resolve stays governed (§10, address ≠ dereference).

---

## The one-line distinction
**Assembly layers become the resource** (their fields ARE the VM's spec, with provenance). **`reference_data` layers stay separate** (the VM references them, dual-anchored, resolved on demand). Same "layer" record type, two roles — and orthogonal context (app_profile, DC-info) is always the second.
