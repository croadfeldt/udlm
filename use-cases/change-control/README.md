# change-control — when changes happen, and who decided

Eight cases adding the temporal layer to class versioning: the change-management policies that
control, gate, and orchestrate *when* an upstream class change reaches an estate and its
downstream records. One upstream change meets varying regimes — continuous adoption (dev),
maintenance windows with full ceremony for breaking changes (prod), freezes and break-glass
expedites (regulated) — plus the staged rollout that composes estates into a chain by policy,
and dependency-ordered propagation inside one estate. 004 succeeds only if the system refuses
(the must-reject convention); the rest are expected to work.

Two rules run through every case: scheduling gates control *when*, evidence gates control
*whether* (nothing waives blue/green evidence, ADR-046); and waiting is visible — queued,
windowed, and frozen are typed debt states, so an estate that is behind is provably on-policy
behind, never silently stale (ADR-045's debt discipline, extended). Worked example:
docs/examples/change-control-walkthrough.md. The contracts are proposed pending the
change-control ADR — corpus first, ruling after.
