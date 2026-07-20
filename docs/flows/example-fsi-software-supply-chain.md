# Example (WIP) — an FSI software supply chain as a policy-driven pipeline

> **Status: work-in-progress example, non-normative.** This is not a conformance flow — it is a worked
> example mapping a real-world scenario onto the **post-1.0** UDLM/DCM direction (the convergence lifecycle
> ADR-030, Pattern → Template → System ADR-033, Data · Policy · Provider). Its purpose is to show *how the
> model would carry this* and to surface **what is missing**. Concepts marked *post-1.0* or *gap* are not
> in 1.0.

**What this settles:** whether the model can express a regulated (FSI) software-supply-chain "golden path"
— and what it would take. The short answer: the pipeline is a **Pattern**, **Policy** resolves it into an
input-specific **Template**, and the run is a **System**; most of the machinery already exists, and the
remaining gaps are mostly *adopt-a-standard* plus one genuine modeling question.

## The scenario

*A new version of an upstream open-source library is available. Validate it, rebuild it **from source**
(vendor packages are not trusted), attest it, and roll it out to every consuming application — **event-driven,
FSI-only, in under an hour.***

The pipeline: `Package Available` → **Intake** (sandbox) → **Validate Sources** → **Rebuild** →
**Validate Binaries** → **Attest** (sign, push, update the CMDB) → **Find & PR all consumers** →
**per-consumer CI/CD** → health-gated prod (rollback on failure).

## 1 · The pipeline, mapped to the model

The backbone is the supply-chain flow; each stage's note is the UDLM/DCM construct it maps to, colored by
fit — 🟩 the model covers it · 🟨 adopt an external standard · 🟥 a real gap.

```mermaid
flowchart TD
    EVT([📦 Package Available<br/>upstream new version · event-driven]):::gap

    subgraph INTAKE[Intake]
        direction LR
        I1[Notification] --> I2[Download source → sandbox]
    end

    subgraph VS[Validate Sources]
        direction LR
        VS1[API compat] ~~~ VS2[Vuln scan] ~~~ VS3[Dependency analysis] ~~~ VS4[Provenance] ~~~ VS5[License]
    end

    RB[Rebuild — compiled from source<br/>= trust anchor]:::fit

    subgraph VB[Validate Binaries]
        direction LR
        VB1[ABI compat] ~~~ VB2[Upstream tests] ~~~ VB3[Internal tests] ~~~ VB4[Reproducibility] ~~~ VB5[SBOM gen] ~~~ VB6[Vuln scan]
    end

    subgraph ATT[Attestation]
        direction LR
        A1[Generate] --> A2[Sign] --> A3[Push to repo] --> A4[Update CMDB<br/>version + lifecycle]
    end

    subgraph CONS[Rebuild consumers]
        direction LR
        C1[Calc consumers<br/>of old version] --> C2[Generate PRs] --> C3[Track upgrades] --> C4[Retire old ver<br/>when all upgraded]
    end

    subgraph CICD[Per-consumer CI/CD · fan-out]
        direction LR
        P1[CI + merge] --> P2[Dev + test] --> P3[Staging + integration] --> P4[Prod canary/BG] --> P5{Health?}
        P5 -->|healthy| OK([✅ success]):::fit
        P5 -->|bad| RBK([↩ rollback]):::fit
    end

    EVT --> INTAKE --> VS --> RB --> VB
    VB -->|event → pipeline| ATT --> CONS --> CICD

    EVT -.-> ME[["▸ external event-source Provider — GAP"]]:::gap
    INTAKE -.-> MI[["▸ event trigger + sandbox isolation Policy (FSI floor)"]]:::fit
    VS -.-> MVS[["▸ process-validation evidence (ADR-003) + provenance<br/>ADOPT · SLSA / OSCAL for gate vocab"]]:::adopt
    VB -.-> MVB[["▸ validation evidence + SBOM output<br/>ADOPT · SPDX / CycloneDX"]]:::adopt
    ATT -.-> MA[["▸ attestation (ADR-022 / ADR-005) — wire subjects<br/>+ provider writes REALIZED (intent ↔ realized)"]]:::fit
    CONS -.-> MC[["▸ dependency-graph traversal (ADR-010)<br/>GAP · graph-gated retirement · fan-out orchestration"]]:::gap
    CICD -.-> MCD[["▸ each consumer = a System · dep bump = Intent → Converge → Realized<br/>health-gate + rollback = the convergence loop"]]:::fit

    NOTE[["Whole flow = an event-triggered COMPOSITE PROCESS (entity_type: multi Process)<br/>work-product nature = an open post-1.0 question · &lt;1hr end-to-end = a composite-process SLA (not yet modeled)"]]:::note

    classDef fit fill:#e8ffe8,stroke:#16a34a,color:#111
    classDef gap fill:#ffe4e4,stroke:#dc2626,color:#111
    classDef adopt fill:#fff2cc,stroke:#d97706,color:#111
    classDef note fill:#eef2ff,stroke:#6366f1,color:#111
```

## 2 · The insight — it is a *policy-driven* pipeline

The build mechanisms change with the input (source code vs a package vs a container), and the checkpoints
that apply change too — but the **pipeline and its checkpoints are the same shape**. That is exactly the
**Data · Policy · Provider** triad and the **Pattern → Template → System** resolution:

- **The pipeline + checkpoints = a Pattern** — the invariant design.
- **The input + its type = the Intent (Data).**
- **Policy resolves the Pattern into a Template** for that input: it **selects the Provider at each stage by
  capability match** (ADR-004) — `compile-from-source`, `verify-signed-package`, `rebuild-container-layer`
  all satisfy the *same* stage intent with different mechanisms (the naturalization boundary, DCM ADR-023) —
  and it **activates the gates that apply** (ABI-compat for a compiled binary, layer-scan for a container,
  provenance for everything). The FSI profile sets the floor.
- **The run = a System / Process instance (Realized).**

So *"mechanisms change by input"* is the **Provider** abstraction working as designed, and *"policy-driven"*
is the **Policy** abstraction selecting providers and gates. "Same pipeline, different components" is simply
**one Pattern → many Templates**.

```mermaid
flowchart TD
    subgraph IN[Input = Intent · Data]
        direction LR
        IN1[Source code] ~~~ IN2[Package] ~~~ IN3[Container] ~~~ IN4[…]
    end

    POL{{"Policy resolves the pipeline<br/>▸ select provider per stage by capability (ADR-004)<br/>▸ activate the gates that apply<br/>▸ FSI profile floor"}}:::pol
    IN --> POL

    subgraph SPINE["Invariant pipeline + checkpoints = the PATTERN"]
        direction LR
        S1[[Intake]] --> S2[[Validate<br/>Sources]] --> S3[[Rebuild]] --> S4[[Validate<br/>Binaries]] --> S5[[Attest +<br/>update CMDB]] --> S6[[Rebuild<br/>consumers]] --> S7[[Per-consumer<br/>CI/CD]]
    end
    POL ==>|"resolves → Template"| SPINE

    S3 -. "mechanism varies by input" .-> RBP[["Rebuild provider:<br/>compile-from-source · verify-signed-package · rebuild-container-layer<br/>same intent, different naturalization (DCM ADR-023)"]]:::fit
    S2 -. "gates vary by input" .-> VSG[["Active gates: provenance (all) · license · vuln<br/>· ABI (compiled) · layer-scan (container)"]]:::fit

    RUN([Run = System / Process instance · Realized]):::fit
    SPINE ==>|Converge| RUN

    GAP[["Open question: policy-COMPOSED constituent set<br/>(policy assembles which providers + gates fire, vs a static constituents[] list)"]]:::gap

    classDef pol fill:#ede9fe,stroke:#7c3aed,color:#111
    classDef fit fill:#e8ffe8,stroke:#16a34a,color:#111
    classDef gap fill:#ffe4e4,stroke:#dc2626,color:#111
```

## 3 · Where it fits, and where the gaps are

**Fits the model as-is** (the parts worth leading with): the estate *is* the "CMDB" — attestation writes
**Realized** state into it; "calculate all projects consuming the old version" is a **dependency-graph
traversal** (ADR-010); each consumer upgrade is a new **Intent → Converge → Realized** with a health gate and
rollback; and the per-input mechanism/gate variance is the **Provider + Policy** model doing its job.

**Gaps — what it would take:**

| # | Gap | Disposition |
|---|-----|-------------|
| 1 | Supply-chain artifact type (version, SBOM, attestation, provenance) | **Adopt** SPDX/CycloneDX (SBOM) + in-toto/**SLSA** (attestation) — don't invent (T5) |
| 2 | External event ingestion ("watch upstream → emit *Package Available*") | Model an Information-Provider / event source; the external-world → trigger edge |
| 3 | Validation gates as declared Policy (vuln thresholds, license allowlist, reproducibility) | **Adopt** SLSA levels / OSCAL for the gate vocabulary |
| 4 | Graph-gated retirement ("retire old version once *all* consumers converged") | A lifecycle policy gated on a dependency-graph predicate |
| 5 | Consumer fan-out orchestration (N consuming projects, each its own CI/CD convergence) | A Template-of-Templates / governed process fan-out |
| 6 | Attestation subjects wired end-to-end (realization / capability / operations) | Known open work |
| 7 | Work-product Process nature + `<1hr` end-to-end SLA | The open post-1.0 "does *work-product* survive as a nature?" question; a composite-process SLA is not yet modeled |

**The one modeling question to settle with engineering:** can a composite Process's **constituent set be
policy-composed** — policy assembles which providers and which gates fire, from the input — rather than a
static `constituents[]` list? This is the Intent → Requested resolution extended to *process composition*,
and it is the crux of "policy-driven pipeline."

## Where each piece is specified
| Piece | Home |
|---|---|
| Intent / Requested / Realized · Converge | ADR-030 · [lifecycle-convergence](lifecycle-convergence.md) |
| Pattern → Template → System (assembly) | ADR-033 · [template-assembly](template-assembly.md) |
| Provider capability match; naturalization | ADR-004 · DCM ADR-023 |
| Process validation evidence + freshness | ADR-003 |
| Dependency-graph completion | ADR-010 |
| Attestation / trust | ADR-005 · DCM ADR-022 |
