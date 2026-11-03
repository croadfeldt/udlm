# Step 4 — the four states

One VM, four records, four authors. Open these side by side; they are the same `app-01`:

| Record | File | Who writes it | What it adds |
|---|---|---|---|
| Intent | [`example-vm-app01-intent-record.yaml`](../../registry/examples/example-vm-app01-intent-record.yaml) | a person, or a tool acting for one | what is wanted: `fields` only |
| Requested | [`example-vm-app01-requested-record.yaml`](../../registry/examples/example-vm-app01-requested-record.yaml) | the control plane | what was decided: defaults filled from layers, policies applied, a provider chosen, a dispatch receipt saying which fields the provider may act on |
| Realized | [`example-vm-app01-realized-record.yaml`](../../registry/examples/example-vm-app01-realized-record.yaml) | the provider | what was built: `outputs`, `dependencies`, `status`, `correlation_ids` |
| Discovered | [`example-vm-app01-discovered-record.yaml`](../../registry/examples/example-vm-app01-discovered-record.yaml) | a scan | what is actually there, in the provider's own terms, matched back to the entity by a correlation id |

## Do this

1. Read `fields.cpu` in all four. Intent says `count: 4`. Requested adds `sockets` and
   `cores_per_socket` — a policy filled them, and `provenance` says which one. Realized repeats
   them: that is what was built. Discovered reports what the scan saw.
2. Follow the links. Requested has `intent_ref` pointing at Intent's `record_uuid`. Realized has
   `requested_ref`. Each link carries a `_head` hash of the record it points at, so a changed
   predecessor is caught.
3. Compare Realized with Discovered. When they disagree, that is drift. Nothing in UDLM decides
   what to do about drift; it only makes the disagreement visible.

## The rule under it

A record is never edited. A change is a new record that `supersedes` the old one; the old one
stays. That is why every record has its own `record_uuid`, and why the four of them can be laid
side by side months later and still tell the story.

## Done when

You can say, for each of the four files, who wrote it and what it added — and you can say what
"drift" means by pointing at two of them.

Next: steps 5 to 10 — relationships, layers, the gates, your own class, checking yourself, where
next — once these four read well.
