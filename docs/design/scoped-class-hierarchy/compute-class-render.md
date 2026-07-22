# Compute — Class-paradigm render (illustrative)

**Illustrative, not a validating file** — the `extends` / Base-Class composition needs the meta-schema change that is *part of* the paradigm. This shows the shape the conversion produces, and which drift each reconciliation fixes.

---

## `Compute` — Base Class  (`compute.json`)
Shared surface, reconciled. Every element here is a `SharedDataElement` at `Compute` scope, inherited by every Compute Type Class.

```jsonc
{
  "class": "base",                         // NEW meta-schema field: base | type | provider
  "resource_type": "Compute",              // single-segment Base Class name (Category)
  "family": "Resource",
  "spec": {
    "properties": {

      // ── cpu ── unifies vcpu (VM) / cpu (BareMetal) / resources.cpu (Container).
      //    These are the SAME concept under three names today — the sweep's name-match
      //    missed it; the Base Class both renames AND shares it. Provider naturalizes.
      "cpu": {
        "type": "object",
        "properties": {
          "count":            { "type": "integer", "minimum": 1, "description": "vCPUs / cores; provider maps to its native model (kubevirt domain cpu, vSphere sockets*cores, EC2 vCPUs)." },
          "sockets":          { "type": "integer", "minimum": 1, "description": "Optional topology hint; provider-support-dependent." },
          "cores_per_socket": { "type": "integer", "minimum": 1 }
        }
      },

      // ── memory ── reconciles the DRIFT the sweep found: VM had {hugepages,size},
      //    BareMetal had {size}. Hugepages becomes an OPTIONAL Base element.
      "memory": {
        "type": "object",
        "properties": {
          "size":      { "type": "string", "pattern": "^[0-9]+(Mi|Gi|MB|GB|TB|MiB|GiB|TiB)$" },
          "hugepages": { "type": "object", "properties": {
              "enabled":   { "type": "boolean" },
              "page_size": { "type": "string", "description": "e.g. 2Mi, 1Gi." } } }
        }
      },

      // ── storage ── the reference-discipline requirements descriptor (PVD-001),
      //    unifying VM disks[].storage / BareMetal storage / Container resources.
      //    Provider matches to a native backing; realized class in outputs.
      "storage": {
        "type": "object",
        "properties": {
          "tier":                { "enum": ["standard","performance","archive"] },
          "min_iops":            { "type": "integer", "minimum": 0 },
          "min_throughput_mbps": { "type": "integer", "minimum": 0 },
          "min_replication":     { "type": "integer", "minimum": 1 },
          "encryption":          { "type": "boolean" }
        }
      }
    }
  }
}
```

**Deliberately NOT in the Base Class:** `network`. The sweep flagged it as a *naming collision*, not shared drift — Cluster's `network` is pod/service CIDRs, Container's is ports, VM's is NIC attachment. Three different concepts; forcing them into one Base element would be false unity. Each stays on its Type Class (and the names may want disambiguating).

---

## `Compute.VM` — Type Class  (`compute.vm.json`)
Extends the Base Class; carries only what is VM-specific.

```jsonc
{
  "class": "type",
  "resource_type": "Compute.VM",
  "extends": "Compute",                    // NEW: the Liskov extends link (add/refine, never contradict)
  "family": "Resource",
  "entity_type": "single",
  "spec": {
    "properties": {
      // cpu / memory / storage are INHERITED from Compute — not restated here.
      "instance_size": { "enum": ["small","medium","large"], "description": "Alt to cpu/memory: size by class (oneOf with the Base cpu/memory)." },
      "guest_os":      { "oneOf": [ { "$ref": "../data-reference.schema.json#/$defs/data_reference" }, { "type": "object" } ] },
      "disks":         { "type": "array", "description": "Per-disk boot_order + storage requirements (refines the Base storage per-disk)." },
      "run_state":     { "type": "object", "properties": { "desired_state": { "enum": ["running","stopped","suspended"] } } },
      "placement":     { "type": "object", "description": "location_ref / zone / affinity (handle-resolved)." },
      "networks":      { "type": "array",  "description": "NIC attachment + ip_address_ref → Network.IPAddress." }
    }
  }
}
```

**Effective wire schema** (what a peer sees, ADR-008): `Compute` ⊕ `Compute.VM`, flattened, `additionalProperties:false` — i.e. `{cpu, memory, storage, instance_size, guest_os, disks, run_state, placement, networks}`. The layering is authoring-time only; the wire stays flat.

---

## What this render demonstrates
- **Drift fixed structurally:** `memory` hugepages divergence and the `cpu` name-fork (vcpu/cpu/resources.cpu) can no longer drift — they are one element.
- **Reference-discipline inherited:** `storage` is requirements-based once, at the Base, for every Compute type.
- **Collision surfaced, not papered over:** `network` correctly stays type-specific.
- **Instantiability (§4):** a bare `Compute` request (just cpu/memory/storage) is realizable — Placement picks VM/BareMetal, policy-fill completes the type-specific blanks.
- **Sibling Type Classes:** `Compute.BareMetalHost` (bmc/bios/identity/architecture), `Compute.Container` (image/command/runtime/ports), `Compute.Cluster` (release/node_pools/CIDRs — the loosest member). VM + BareMetalHost share the richest "compute instance" surface; Container/Cluster are looser.
