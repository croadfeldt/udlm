# Step 7 — the gates

Every rule in UDLM that can be checked by a program is checked by one, on every change. The checks
are called gates. A pull request that fails a gate does not merge, and a gate's message names the
rule and the file.

## Do this

1. List them:

```bash
python3 scripts/ci-steps.py | cut -f1
```

   About eighty lines. Each is one step of `.github/workflows/validate.yml`; the list is read from
   that file, never retyped, so it cannot drift.
2. Run a few. The validator you used in step 2 is one gate. Pick two more by name:

```bash
./scripts/signoff.sh --only 'Liskov|graph integrity'
```

   The script says it is running a subset and that a subset is not signoff.
3. Run them all once, so you know what it costs:

```bash
./scripts/signoff.sh
```

   Two to three minutes. Every gate, then a short checklist of the judgments no gate can make.
   This is what you run before you open a pull request.

## What a shipped example needs

In step 2 you wrote a record and the validator said ok. A record that ships in `registry/examples`
has to pass more than the validator, and the two things it will ask you for first are:

- **A header that says what the example proves.** Two comment lines at the top:
  `# asserts: <rule ids>` and `# proves: <one sentence>`. Open the intent record from step 2 and
  read its header; gate ECV-001 checks that the rule ids are real.
- **No private names.** Hostnames and addresses from a real estate fail the estate-token gate.
  Examples use `example.com` and the RFC 5737 address ranges.

After a class change, five derived files move with it; `./scripts/regen.sh` regenerates them all.

## Done when

The full signoff printed `Automated gates PASS`, and you can say, for one gate you picked, which
rule it holds and which file it would name if that rule broke.

Next: [Step 8 — your own class](08-your-own-class.md).
