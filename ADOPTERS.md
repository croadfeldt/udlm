# Adopters

Implementations and estates that run on UDLM. An adopter is listed when it validates its records
against the registry on every change, or runs the conformance suite against them.

| Adopter | What it runs | Since |
|---|---|---|
| A private homelab estate (the maintainer's) | Every resource as UDLM state records; validated against a pinned UDLM commit on every change; the conformance suite judged 1,925 records on 2026-10-29 | 2026-08 |
| A control-plane fork (the maintainer's) | Writes per-state UDLM records for the resources it provisions; vendors the record schemas | 2026-09 |

To be listed, open a pull request adding a row, with a link to where the validation runs.
