# Step 5 — edges

A VM sits on a host, uses a volume, holds an address. UDLM writes those as edges on the record,
and nothing else: there is no "bundle" type, no stack object, no parent that owns children. The
graph is the edges.

## Do this

1. Open [`registry/examples/example-vm-app01-realized-record.yaml`](../../registry/examples/example-vm-app01-realized-record.yaml)
   and find `dependencies`. Three edges. Each has:
   - `edge_type`: one of four words. `depends_on` (needs it to run), `contained_by` (lives inside
     it), `binds_to` (takes a value from it), `references` (points at it, nothing more).
   - `target_uuid` and `target_handle`: the other thing's identity, and its readable name.
   - `strength`: `hard` means the VM cannot exist without it.
   - `resolved_at`: when the link was made.
2. Look at the third edge. It `depends_on` an IP address and carries `bound_field:
   outputs.primary_ip`. That is how an output on one thing becomes an input on another: the edge
   says which field is bound, so a change at the far end is traceable to this record.
3. Open the discovered record's `dependencies`. The scan did not know the uuids; it found a host by
   its SMBIOS uuid and a disk by a provider path, and wrote those as `target_key`. Matching a key
   back to an entity is the control plane's job, not the record's.

## Why only four words

Every richer vocabulary somebody proposed (runs-on, mounts, attached-to, member-of) collapses into
these four plus the class of the target. A VM that `contained_by` a host and `depends_on` a volume
says everything "runs on" and "mounts" would, and a tool only has to understand four edge types to
walk the whole estate.

## Done when

Run:

```bash
python3 tests/check_graph_integrity.py
```

It prints a node count and `0 integrity violation(s)`. Then say, for each of the three edges on
the realized record, which of the four words it uses and why that one.

Next: [Step 6 — a layer](06-a-layer.md).
