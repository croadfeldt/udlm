# Step 8 — your own class

A provider that can build VMs has limits the portable class does not: at most 64 CPUs, memory in
fixed sizes, a namespace to put things in. A Provider Class says that. It sits under `Machine.VM`,
narrows what the parent allows, and adds what only this provider needs.

## Do this

1. Open [`registry/examples/classes/resource/compute/machine/vm/cexample-cloud.yaml`](../../registry/examples/classes/resource/compute/machine/vm/cexample-cloud.yaml).
   Read the header: `class: provider`, `resource_type: Machine.VM.CExampleCloud`, `parent:
   Machine.VM`. The name shows the ancestry, one segment per tier.
2. Read the first element, `cpu`. The parent said `count` has a minimum of 1 and no ceiling. This
   provider sets a maximum of 64. That is a narrowing: a child may tighten what its parent allows
   and may never loosen it. The Liskov gate checks that, down to nested properties.
3. Read `namespace`. The parent has no such element; this provider adds one, and marks it required.
   An added element is the provider saying "I need this to build anything."
4. Read a `supports` block. It is the provider's offer: the range of values it can satisfy, which is
   also the menu a consumer picks from. A request is this file with every range collapsed to one
   value.

## Make one

Copy that file to a sibling, `my-cloud.yaml`. Replace every `Machine.VM.CExampleCloud` with
`Machine.VM.MyCloud`, change the `uuid`, and in `cpu` set both the schema `maximum` and the
`supports` `max` to 32. Then:

```bash
python3 tests/check_class_liskov.py
./scripts/regen.sh
```

Liskov reports one more class and no violation. `regen.sh` adds your class to the pin manifest; a
class is not done until the derived files are committed with it.

Now break it, twice. Set the schema `minimum` under `cpu.count` to 0 and run Liskov: it refuses,
saying 0 is below the parent's 1, "looser, not a refinement". Put it back, set the `supports`
`max` to 64 while the schema still says 32, and run it again: it refuses, because an offer may
narrow what is valid and never exceed it. Delete your file and run `./scripts/regen.sh` once more;
the pin manifest goes back to what it was.

## Done when

You saw Liskov accept the narrowing and refuse both loosenings, and `git status` shows no change
under `registry/`. The full procedure, with every gate named, is
[`docs/authoring/scoped-class.md`](../authoring/scoped-class.md).

Next: [Step 9 — checking yourself](09-checking-yourself.md).
