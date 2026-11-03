# Step 2 — say what you want

An intent record is the one a person writes. It says what you want, nothing about how. You will
copy one and change three values.

## Do this

1. Copy [`registry/examples/example-vm-app01-intent-record.yaml`](../../registry/examples/example-vm-app01-intent-record.yaml)
   to `registry/examples/example-vm-mine-intent-record.yaml`.
2. Change three things:
   - `handle`: a name of your own, lowercase, such as `lab/vm/mine-01`;
   - `fields.cpu.count`: `2`;
   - `fields.memory.size`: `4Gi`.
3. Give the record its own identities. `entity_uuid` is a random v4 uuid (`python3 -c "import uuid;
   print(uuid.uuid4())"`). `record_uuid` is a v7 uuid; the simplest way is to take the example's and
   change its last digits.
4. Check it:

```bash
python3 registry/tools/validate.py
```

The line for your file should say `ok`. If it says `FAIL`, the lines under it name the field and
what it expected.

## What you did not have to write

Everything a machine knows better than you: who will build it (`provider`), what it will get
(`outputs`), where it landed (`sovereignty.locality`), the hash chain. An intent record carries
the envelope, `fields`, and `provenance` saying who set each field. The rest arrives on the later
records.

## Done when

`validate.py` says ok for your file. Keep it for now; step 4 puts it beside the other three records.
It is yours to learn with, not to commit: a shipped example has to say what it proves, and step 7
covers that.

Next: [Step 3 — where the shape comes from](03-where-the-shape-comes-from.md).
