# Step 3 — where the shape comes from

The validator knew that `cpu.count` must be a number and `memory.size` a quantity. It knew from the
class. A class is written once and served compiled; you will look at both.

## Do this

1. Open [`registry/classes/resource/compute/machine/vm.yaml`](../../registry/classes/resource/compute/machine/vm.yaml).
   This is `Machine.VM` as its author wrote it. Find `elements:`. Each element is one field a VM
   has, with its `schema` and a sentence saying what it is for. Find `cpu`.
2. Notice `parent: Machine`. A VM is a kind of Machine, and `Machine` is written in
   [`registry/classes/resource/compute/machine/_base.yaml`](../../registry/classes/resource/compute/machine/_base.yaml).
   Find `cpu` there too. The parent says what every machine's CPU field is; the VM says only what
   it adds or requires, such as `count` being mandatory. A child refines its parent and never
   contradicts it; a gate checks that.
3. Open [`registry/generated/machine.vm.json`](../../registry/generated/machine.vm.json). This is
   the served spec: the parent's elements and the VM's own, compiled into one flat shape. It is
   what `type_ref` on your record points at, and what the validator used.
4. Find `outputs` in the same file. Those are the fields a provider reports back after it builds a
   VM — the ones step 1 called "what came back".

## Three tiers

A class sits in one of three tiers, and the tier says how portable its fields are:

- **Base** — what every provider of this kind of thing can fill: `Machine`.
- **Type** — one shape of it: `Machine.VM`, `Machine.BareMetalHost`.
- **Provider** — one provider's own fields, portable to nobody else: `Machine.VM.CExampleCloud` is
  the worked example.

The validator holds an intent record to the Base and Type elements. Provider fields are allowed
only when the record names that provider.

## Done when

You can point at the line that defines `cpu.count`, say which tier it lives in, and say what the
difference is between the authored class and the served spec.

Next: [Step 4 — the four states](04-the-four-states.md).
