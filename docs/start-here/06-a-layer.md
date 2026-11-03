# Step 6 — a layer

In step 4 the requested record had values nobody wrote in the intent: `sockets`, `cores_per_socket`.
A layer put them there. A layer is a record of values an estate applies to requests before a
provider sees them: defaults, and bounds that nothing below may cross.

## Do this

1. Open [`registry/examples/example-layer-limits-baseline.yaml`](../../registry/examples/example-layer-limits-baseline.yaml).
   Skip the comment and read from `record_type: layer`. It sets one value (`fields`) and bounds
   two (`limits`): retention between 7 and 90 days, memory up to 384Gi in 8Gi steps, each with a
   `reason`.
2. Open [`registry/examples/example-layer-extends-multi.yaml`](../../registry/examples/example-layer-extends-multi.yaml).
   It `extends` the first one and tightens: retention 30 to 90. Tighter is allowed. Wider is not.
3. Prove that. Copy the second file to a new file beside it, `example-layer-mine.yaml`, give it a
   new `uuid` and `handle`, and change its retention `min: 30` to `min: 5`. Run:

```bash
python3 tests/check_layer_limits.py
```

   You get a `LIM-003` line that names your layer, the field, the clause you wrote, the layer
   whose envelope it broke, who owns that layer, and the reason that layer gave. That is the whole
   point: a refusal always says who forbade what and why. Delete your file afterwards.

## The order

Layers stack, lowest authority first: `base`, `core`, `intermediate`, `service`, `request`. A higher
layer overrides a lower one field by field. `policy` layers apply over the merged result, and a
compliance-class policy overrides everything, including what the consumer asked for. Every field
in the merged result carries which layer set it; step 4's `provenance` is that trail.

UDLM ships no defaults. These examples are `example.com` content; the values your estate wants live
in your estate's own layers. UDLM checks that a layer is well formed and inside its parents. What
to do when a request breaks a bound is a policy, and that is the estate's call.

## Done when

You saw the `LIM-003` refusal and can say which of its parts answers "who", "what" and "why".
To write a real one: [`docs/authoring/layer.md`](../authoring/layer.md).

Next: [Step 7 — the gates](07-the-gates.md).
