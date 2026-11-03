# Start here

A walk through UDLM, one short step at a time. Each step does one thing and ends with a command
that proves it worked. Do them in order; each builds on the last. Thirty minutes at a time is
plenty. The fast version of steps 1 to 4 is [`docs/guides/quickstart.md`](../guides/quickstart.md);
this is the slow one.

## Step 0 — what UDLM is

UDLM is a way of writing down infrastructure so that any tool can read it.

Three ideas carry everything:

1. **A thing.** A VM, a volume, a network, a job. Every thing has one identity for life.
2. **Four records about it.** What someone *intended*, what the system *requested* of a provider,
   what the provider *realized*, and what a scan later *discovered*. Four records, four authors,
   never edited, only replaced.
3. **A class that says its shape.** `Machine.VM` says a VM has `cpu`, `memory`, `disks` and so on,
   which of those are portable to any provider, and what the provider reports back.

Everything else — layers, policies, conformance — is built on those three. If you remember one
sentence: *records say what is, classes say what shape, and nothing is ever edited in place.*

## The steps

| Step | You will | Done when |
|---|---|---|
| [1. Read one record](01-read-one-record.md) | read a realized VM record with a key to every field | you can say what each field is for |
| [2. Say what you want](02-say-what-you-want.md) | write an intent record by copying one and changing three values | the validator says ok |
| [3. Where the shape comes from](03-where-the-shape-comes-from.md) | open the class and find where `cpu.count` is defined | you can point to it |
| [4. The four states](04-the-four-states.md) | read the four records of one VM side by side | you can say who writes each one |

Steps 5 to 10 — relationships, layers, the gates, your own class, checking yourself, where next —
follow once these four read well.
