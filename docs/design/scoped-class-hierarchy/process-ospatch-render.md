# Render — Process.OSPatch: engine blue today, engine green tomorrow, one declared class

**What this settles:** the Process-family class model exercised on a real migration — OS patching
realized by the incumbent engine (blue), migrating to the successor engine (green), with the
*declared process classes unchanged throughout*.
The punchline the walkthrough proves: **engine migration is a provider swap on an untouched Type**
— the same operation, machinery, and audit continuity as moving a VM between providers.

## Base Class: `Process` (thin, shared by every process)

```yaml
class: Process
elements:
  inputs_schema:        {scope: base, schema: json-schema, purpose: typed parameters the run accepts}
  outputs_schema:       {scope: base, schema: json-schema, purpose: typed results the run publishes}
  idempotency:          {scope: base, values: [idempotent, at-most-once, unsafe-repeat]}
  timeout:              {scope: base, schema: duration}
  retry_policy:         {scope: base, schema: {max_attempts, backoff}}
  compensation:         {scope: base, values: [none, declared], purpose: what undo means, if anything}
  affected_entities:    {scope: base, purpose: which records this run may mutate — the blast-radius declaration}
```

## Type Class: `Process.OSPatch` (the portable definition — the thing both engines share)

```yaml
class: Process.OSPatch
extends: Process               # Liskov: adds/refines, never contradicts
elements:
  targets:              {refines: inputs_schema, schema: reference-list -> Compute.* hosts or a DCMGroup}
  patch_policy:         {values: [security-only, all-updates, cve-list], cve_list: optional}
  reboot_policy:        {values: [never, if-required, always], window_ref: optional -> maintenance window}
  exclusions:           {schema: package-name list, purpose: holds the org's known-fragile packages}
  # declared effects — what a conformant run is ALLOWED to change:
  effects:              {refines: affected_entities, value: "targets' SoftwarePackage state; power (reboot) within reboot_policy"}
  # typed outputs every engine must publish (the E2 surface of a process type):
  outputs:
    patched:            {schema: reference-list, purpose: hosts fully patched}
    failed:             {schema: reference-list + reason}
    rebooted:           {schema: reference-list}
    package_delta:      {schema: per-host package change-set, purpose: feeds SoftwarePackage/SBOM records}
idempotency: idempotent        # patching to a policy level converges
compensation: none             # rollback is a DIFFERENT process type; declared honestly
```

Nothing above names an engine. This is what the org's policy gates, what schedules reference,
what compliance reports against — and what both providers must satisfy to declare support.

## Provider Class: `Process.OSPatch.EngineBlue` (today — the incumbent)

```yaml
class: Process.OSPatch.EngineBlue
extends: Process.OSPatch
elements:
  definition_ref:       {scope: provider, value: "org-patching/apply", version_pin: "~> 4.2"}
  control_server:       {scope: provider, schema: reference -> the engine's control-plane Software.Service}
  execution_order:      {scope: provider, purpose: where in the engine's host execution sequence this runs}
  start_jitter:         {scope: provider, schema: duration, purpose: per-host start-time spread}
```

Registration: the blue engine's provider declares `execute_workflows / Process.OSPatch` in its
capability set. Admission (PRV-009), trust, and audit apply as for any provider.

## Provider Class: `Process.OSPatch.EngineGreen` (tomorrow — the successor)

```yaml
class: Process.OSPatch.EngineGreen
extends: Process.OSPatch
elements:
  definition_ref:       {scope: provider, value: "os-patch @ the org automation repo", version_pin: release tag}
  execution_env:        {scope: provider, purpose: the engine's execution-environment image}
  target_source:        {scope: provider, values: [static, estate-derived], note: estate-derived = the estate IS the target list}
  rolling_batch:        {scope: provider, schema: int|percent, purpose: rolling batch size}
```

Same Type extended, different engine vocabulary. Neither provider class leaks into the other —
or into the Type.

## The migration, step by step (no class changes at any step)

1. **Both declared.** The green engine's provider registers, declaring `execute_workflows /
   Process.OSPatch`. Two providers now satisfy the Type — the same state as a resource type with
   two eligible providers. Default-deny: the platform admin admits the new capability.
2. **Canary by policy.** A placement/validation policy routes a slice (one host group; `rolling_batch`
   makes this natural) to the green provider. The org's patch *intent* — targets, patch_policy,
   reboot_policy, window — is untouched: it lives at Type scope.
3. **Comparable by construction.** Both engines publish the same typed outputs (`patched`,
   `failed`, `package_delta`), so the canary comparison is a query, not a spreadsheet — and
   compliance reporting doesn't notice the engine at all.
4. **Blue/green, not just canary.** Because the process is declared idempotent and both engines
   publish identical typed outputs, the migration supports true blue/green: run green
   against targets blue just converged — a conformant green run's `package_delta` is ≈
   empty, and any non-empty delta is a *behavioral difference between engines*, surfaced as data
   before cutover. Engine testing becomes a diff of outputs, not a leap of faith; the same
   mechanism later regression-tests engine upgrades (engine-green N → N+1) against themselves.
5. **Cutover = placement preference.** Policy flips provider preference; the scheduled patch
   process (a `lifecycle/scheduled-requests` entity referencing the Type) re-places onto the green
   engine.
   The schedule record's UUID and history are continuous — runs before and after instantiate the
   SAME Type, so the audit trail reads as one unbroken practice with an engine change, not two
   unrelated automations.
6. **Blue retires.** The blue provider's capability is de-admitted; its Provider Class stops being
   selectable; its elements remain in history (custodied, never round-tripped). If the blue engine
   ever returns, the class is still defined.

## What this proves about the design

- **Portability read structurally:** everything the org cares about sits at Type scope; only
  `definition_ref`-tier bindings are engine-bound. "How locked-in is our patching?"
  is answered by *looking at where the elements sit.*
- **The migration used zero new machinery** — capability declaration, admission, placement,
  typed outputs, scheduled requests, audit: all existing. The class system's contribution was
  making the Type the stable thing the org's intent attaches to.
- **The shared-capability declaration is the linchpin** (the maintainer's point that corrected
  this plan): without multiple providers declaring one Type, none of the above is expressible.
