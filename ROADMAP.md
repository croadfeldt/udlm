# Roadmap

UDLM is at `udlm/0.1`. The path to `udlm/1.0` is one document, kept current:
[`registry/UDLM-1.0-LOCKDOWN.md`](registry/UDLM-1.0-LOCKDOWN.md) — what 1.0 promises, the
freeze, every open issue sorted into blockers and 1.x, the work packages, and the exit criteria.

## Now

- Close the remaining 1.0 blockers (the plan's §4.1).
- Finish the readability sweep, area by area, under the gate (row 138).
- Promote parts from experimental to candidate to stable by the graduation ladder (register
  row 145), as a running implementation's conformance reports arrive.

## Then

- Tag `udlm/1.0-rc1`, hold 30 days with no breaking change, tag `udlm/1.0` on the maintainer's
  go (`registry/VERSIONING.md`, the cut procedure).

## After 1.0

Everything labelled `1.x` in the issue tracker: additive work that waits for the tag — the
operations family, true intent, the SDK, the HTTP-level conformance checklist.

## Where this project wants to live

The CNCF. This repository carries the Sandbox eligibility files (`MAINTAINERS.md`, `SECURITY.md`,
`CODE_OF_CONDUCT.md`, `ADOPTERS.md`, this roadmap, `CONTRIBUTING.md`), the spec's change process
(the register) and its conformance suite (`CONFORMANCE.md` §8). An application is the
maintainers' call, not a date.
