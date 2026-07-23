# Best practices — authoring custom Base, Type, and Provider classes

**Audience:** an organization (or provider) standing up its **own** classes under the scoped-Class paradigm.
**Status:** design guidance (non-normative) applying ADR-038 (*Authorship & domain*) and its DCM realization
(ADR-025). Not a rule family — it cites existing rules, defines none.

UDLM defines the **spec** for Base/Type classes and ships a **canonical library**; **any authority may author its
own classes** under that spec, as a **DCM policy/profile-driven feature** (ADR-038 *Authorship & domain*). This
page is the how-to for doing that well. The whole discipline reduces to one sentence:

> **Extend canon under your own authority; never mutate it.**

Everything below is how to hold that line.

## 1. Is a custom class even the right tool?

Most "we need our own class" instincts are a cheaper mechanism. Walk the ladder top-down and author a
class **only** when nothing above it fits:

| If the need is… | Use | Not a class because… |
|---|---|---|
| a **value / default / constraint** on an existing type (must-encrypt, size ≤ X) | **Policy / Profile / layer value** | it's still a canonical `Compute.VM` — a class here fragments interop for zero schema gain (the most common mistake) |
| **extra org data** on an existing type (`cost_center`) | an org-scoped **`SharedDataElement`** (additive, must-ignore-unknown) | additive data is not a new type; peers ignore the unknown |
| **orthogonal context** (a DC bundle, an app profile) | a **references-context edge** (ADR-038) | context is *linked*, not a type |
| a genuinely **new type** the canonical library lacks, *with its own schema* | a **custom Type class** under your authority | ✅ this is the tool |
| a genuinely **new category** the library lacks entirely | a **custom Base class** under your authority | ✅ this is the tool (rare) |
| a genuinely **provider-specific** datum with no vendor-neutral form | a **Provider Class element**, provider-authored | ✅ the provider-scoped tool (§3) |

The gate for the custom-type / custom-base rows is the **earns-its-keep test** (ADR-038 *Naming depth*): real
*shared-then-specialized schema* — fields/vocabulary nothing canonical provides — not a policy or a single extra
field in disguise. The gate for the Provider Class row is **§3**.

## 2. Custom Type vs custom Base

- **Custom Type — the common case.** `acme.example/Compute.GenomicsVM` **extends canonical `Compute`**
  (cross-authority Liskov). A new type inside an existing category: inherit the canonical Base's
  `SharedDataElement`s, add only what's new. Maximal reuse, maximal interop.
- **Custom Base — rare, higher bar.** `acme.example/Genomics` — only when the org owns a whole resource
  *category* UDLM does not model at all. A Base is meant to be broadly shared, so authoring your own means you are
  carrying a category the community lacks: a strong **promotion** candidate, not a permanent private fork.

## 3. Authoring a Provider Class — the provider-authored layer

A **Provider Class** (`Compute.VM.OCPVirt`) extends a canonical **Type Class** with **provider-specific
elements**. UDLM defines the *grammar*; the **provider authors the definition** (ADR-038 *Authorship & domain*).
It is the sanctioned home for a genuinely provider-specific datum — a first-class, **provider-defined
`SharedDataElement`**, not an opaque additive bag.

**When to author one.** Only for a datum that is *genuinely provider-specific* with **no vendor-neutral
(Base/Type) expression** — a construct only that provider has. If the need is an *intent* another provider could
satisfy natively (e.g. `isolation: private`), it belongs at the **Type Class** as a portable requirement, not
here. Provider scope is the last resort, not the default.

**The element.** A `SharedDataElement` at Provider scope — `{scope: Compute.VM.OCPVirt, element, schema, values,
state}`. The **provider owns the schema** of what is inside; UDLM **custodies** it (identity, provenance,
versioning, tenancy) and passes it to the provider to apply. UDLM never renders it into a native spec —
naturalization stays at the provider edge (ADR-023). A Provider Class element carries provider-specific *data*,
never the provider's native/naturalized form.

**Discipline (beyond the general discipline in §4):**
1. **Express intent higher when you can.** Ask whether the datum is truly provider-specific or an intent stated
   in provider terms. Portable intent → Type Class; only the irreducibly-provider-specific → Provider Class.
2. **Structured, not a free-string bag (PVD).** A Provider Class element is reference / codelist /
   requirement-shaped — never an untyped string blob. "Provider-specific" is not a licence to be unstructured.
3. **Add, never shadow.** A Provider Class *adds* provider elements; it never redefines or drops the Type Class's
   canonical elements (Liskov / no-shadow, §7).

**Portability — across the declaring set, not zero.** A Provider Class is **portable across the *set* of
providers that declare it** (ADR-038 §4): more than one provider may declare the same Provider Class, and an
entity ports across that set. Portability narrows to a single target only when a specific provider **instance**
is named (the authority/instance axis, ADR-038 §10). So a Provider Class element degrades portability to *its
declaring set* — flagged, and the consumer notified — never a silent pin to one vendor.

**Grow portability by contributing upward.** A Provider Class element that recurs across providers is a
Type-Class candidate. Contribute it **upward** (Provider → Type) through the gated contribution model (ADR-038
§6): it lands `proposed` at the target scope and canonicalizes by governance, so the intent then ports for
everyone. The recurring-provider-element set is the observable roadmap of what should become canonical.

**Lifecycle.** A Provider Class rides the **same one contribution lifecycle** as Base/Type classes (§6): author
(proposed) → register (Liskov-validated against its Type parent) → use (authority-scoped, policy/profile-governed)
→ promote or retain. Provider-contribution integration is DCM's (`contribution-pipeline.md` §5; ADR-025).

## 4. How to do it well — the discipline

1. **Extend canon, don't reinvent.** Root a custom class at the nearest canonical Base/Type so it inherits shared
   elements. Author from scratch only when nothing canonical fits.
2. **Authority namespace, always.** Custom classes live under `acme.example/…`, never the canonical namespace.
   This is what makes them safe — a distinct identity, canon untouched.
3. **Minimal own-surface.** Reuse canonical `SharedDataElement`s by reference; define only genuinely-new elements.
   Every field you author yourself is a field that will not port beyond your authority.
4. **Liskov, or nothing.** A custom class **adds or refines** — never removes or contradicts — what it extends. It
   must be a valid substitute for its parent; that is what keeps resolution and matching sound.
5. **Author for promotion.** Write clean, `proposed → canonical`-ready elements. If a second org independently
   authors the same custom type, that ≥2-adopter signal is exactly when to promote.
6. **Own the portability trade-off.** A custom class ports across *your* authority, not the federation, until
   promoted. That's fine — just chosen, not accidental.

## 5. Anti-patterns

- **Class-where-a-profile-belongs** — authoring `acme/Compute.VM` for a *policy* need (encryption, tags).
  Fragments interop for no schema gain. The single most common error.
- **Provider-scoping portable intent** — putting at Provider scope a datum another provider could satisfy
  natively (an `isolation` intent stored as a raw vendor construct). Kills portability that a Type-Class
  requirement would keep. Express the intent at the Type Class; reserve Provider scope for the
  irreducibly-provider-specific.
- **Shadowing canon** — a custom class that *redefines* the canonical type it should *extend* (drops/renames
  canonical fields). Forbidden (Liskov / no-shadow).
- **Mid-hierarchy fork** — inserting a custom class *between* canonical layers to intercept resolution. Customs
  are extensions/leaves under your authority, never rewrites of the canonical chain.
- **Premature / speculative custom Base** — a custom category where a custom Type under a canonical Base would do;
  or authoring before the schema need is real.
- **Orphaned customs** — a custom class that clearly generalizes but is never proposed for promotion, leaving the
  federation needlessly fragmented.

## 6. Lifecycle — the one contribution lifecycle, applied to classes

**author (proposed) → register (validated Liskov-conforms to its parent) → use (authority-scoped,
policy/profile-governed) → promote** (broadly-useful → a canonical version) **or retain** (org-specific → stays
under authority). Who may author / register / promote is policy/profile + trust (governance). This is the **same**
register/validate/promote pipeline as data layers and vocabularies — only the data spec differs (ADR-038
*Authorship & domain*; realized in DCM ADR-025). A Provider Class rides this pipeline unchanged (§3).

## 7. The guard — never redefine a canonical class in place

Custom-class authoring is the **alternative** to redefinition — you author *beside* canon, never *over* it.
Redefining a canonical class in place breaks wire-compatibility, violates Liskov / no-shadow, couples org
governance into the substrate (core-tenets **T1/T2**), and fragments the shared type. The **only** legitimate
change to canon is **versioned canonical evolution** — a new version behind the named-head anchor, the immutable
anchor pinning the old (ADR-038 §10 dual anchor), produced by the **promote** stage and shared with everyone.
There is no in-between where one org silently owns a different `Compute.VM`: keep it authority-scoped, or promote
it for all.

| The need | Mechanism |
|---|---|
| Add org data | org `SharedDataElement` (additive) |
| Constrain / standardize | constraint profile / policy / layer value |
| A type canon lacks | **custom Type class** under your authority (extends canon) |
| A category canon lacks | **custom Base class** under your authority (rare) |
| A provider-specific datum | **Provider Class element** under the provider's authority (§3) |
| Improve canon for everyone | **versioned promotion** — the only legitimate "redefinition" |
| Change a field's meaning just for you | don't — add a field, or author your own class |

## Related
- **ADR-038** *Authorship & domain* — UDLM defines the spec + canonical library; any authority authors under it;
  one DCM contribution lifecycle. *Org standards & tenancy* — Policy over shared classes vs authority-scoped
  authoring (the line is **authority, not permission**).
- **DCM ADR-025** / **`contribution-pipeline.md`** — the engine that registers, validates, and promotes
  provider/org-authored classes (§5, provider-contribution integration).
- **`context-and-purpose.md` §7.1 / DCM ADR-023** (naturalization boundary) — a Provider Class element carries
  provider-specific *data*; the substrate never translates it to native form.
- **ADR-041 / DCM ADR-027** — the information-firewall: a class-authoring contribution is an ingress crossing,
  admitted by policy.
- **core-tenets T5** (adopt outward) / **T7** (reduce inward); **`portable-values.md`** (PVD) — reference the
  canonical element, don't restate it, when you extend.
