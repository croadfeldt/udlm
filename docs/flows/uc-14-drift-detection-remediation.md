# UC-14 · Drift detection and remediation — the stage

**What this settles:** the steady-state loop that keeps *realized* honest — compare what the provider actually
has (**discovered** state) against what DCM provisioned (**realized** state), record any divergence as a
classified drift record, and remediate per the recovery policy. A **lighter** flow — it **builds on
[request-realization](request-realization.md)**; this is what runs *after* commit, on a timer, not a new
request.

> **Use Case:** `docs/spec/contracts/drift-detection-remediation`. **Persona:** platform-engineer · **Profile:** standard.

**In one breath.** On the profile's reconciliation cadence, the system probes what the provider really has and
diffs it against the realized record. A divergence becomes a drift record — field by field, with a severity of
info, warning, or critical — and the recovery policy decides what to do about it. The remediation runs, its
result is recorded and verified, and the cycle stays inside the profile's reconciliation window.

## What this adds over request-realization
- **A fifth read: discovered state.** Implementation ends at realized. This loop introduces *discovered* — the
  provider's actual current state, probed live — and makes realized-vs-discovered the thing under watch.
- **Drift is a first-class record.** A divergence is not just a log line: it is a record with a field-by-field
  comparison and a **severity classification** (info / warning / critical) that the recovery policy keys on.
- **Recovery is policy, not a fixed reaction.** What to do about drift — re-converge, alert, quarantine — is a
  recovery policy decision, so different severities and resources can be handled differently.
- **Remediation is verified, not fire-and-forget.** After the action runs, its result is recorded and checked,
  closing the loop rather than assuming success.
- **It is bounded in time.** The whole detect-classify-remediate cycle must complete within the
  profile-governed reconciliation window — a timing guarantee implementation itself never makes.

## The flow — only what's different
```mermaid
flowchart TD
  T["Reconciliation timer (profile cadence)"] --> PR["Probe discovered state<br/>(what the provider actually has)"]
  PR --> D{"Discovered vs realized<br/>— diverged?"}
  D -- "match" --> OK["No drift — cycle recorded"]
  D -- "diverged" --> DR["Drift record<br/>field-by-field + severity"]
  DR --> RP["Recovery policy selects action"]
  RP --> RM["Remediate via provider"]
  RM --> V["Record + verify result<br/>(within reconciliation window)"]
```
The remediating build, where one is needed, is request-realization.

## Success criteria (from the UC)
- Discovered state is probed and compared against realized state.
- Divergences produce drift records with a field-by-field comparison.
- Drift records include a severity classification (info, warning, critical).
- The recovery policy triggers the appropriate remediation actions.
- Remediation results are recorded and verified.
- The drift detection cycle completes within the profile-governed reconciliation window.

## Data · Policy · Provider
- **Data:** discovered and realized states are compared; the drift record (comparison + severity) and the
  verified remediation result are stored.
- **Policy:** the recovery policy governs which remediation runs for a given drift, keyed on severity.
- **Provider:** probed for discovered state, and executes the remediation when one is required.

## Who provides what, and when

The lifecycle answer — the personas, what a request contains, what data is added and **by whom**, why
**nobody sets placement**, and the worked VM-with-network-and-storage example — lives once in
[request-realization § Who provides what, and when](request-realization.md#who-provides-what-and-when).
It holds for every use case.

**This case's delta:** the driving persona is **`platform-engineer`**. Everything that persona relies on —
layers, tenant binding, policies, provider capability — was declared by the others *before* this
request existed, exactly as the lifecycle answer describes.

## Pointers
- Base flow: [request-realization](request-realization.md). UC source: `docs/spec/contracts/drift-detection-remediation`.
