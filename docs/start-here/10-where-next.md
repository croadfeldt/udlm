# Step 10 — where next

You can read a record, write one, find its class, name the four states, walk the edges, bound a
request with a layer, run the gates, write a class, and prove conformance. That is the model. What
is left is depth, and it depends on what you came to do.

## By what you want to do

| You want to | Go to |
|---|---|
| build a control plane, a provider or a tool on the model | [`docs/guides/consuming.md`](../guides/consuming.md) |
| add a resource type, a class, a policy, a layer | [`docs/authoring/README.md`](../authoring/README.md) |
| review someone else's change | [`docs/guides/reviewing.md`](../guides/reviewing.md) |
| join from another organization | [`docs/guides/co-engineering.md`](../guides/co-engineering.md) |
| contribute to the project itself | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |

## The three documents to keep open

- **The decisions register**, [`docs/adr/README.md`](../adr/README.md). Every ruling is a dated
  row, newest on top. When you wonder why something is the way it is, the answer is a row.
- **The road to 1.0**, [`registry/UDLM-1.0-LOCKDOWN.md`](../../registry/UDLM-1.0-LOCKDOWN.md).
  What 1.0 will promise, what is frozen, what waits for 1.x, and the exit criteria.
- **What a version means**, [`registry/VERSIONING.md`](../../registry/VERSIONING.md). The spec and
  each class have their own version; a record pins both.

## What this course left out

Policies (what to do about a value), profiles (a named set of policies), rehydration (rebuilding an
estate from its records), composition (many things requested as one) and federation (records
across organizations). Each has its own spec document under `docs/spec/`, and
[`docs/guides/working-with-udlm.md`](../guides/working-with-udlm.md) is the map.

## One ask

If a step in this course was wrong, slow or unclear, open an issue that names the step. The course
is held to the same gates as the spec, and a reader who was not in the room is the only test that
matters.
