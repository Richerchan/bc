# Scientific Rigor Memory V1

This note captures the manuscript lessons that emerged from the latest review comparing `MANUSCRIPT_V6` against a published npj reference.

## 1. Evidence strength must match system complexity

A systems paper cannot rely on a visually complete architecture plus small aggregate benchmarks alone. As the system description becomes more complete, the paper must also add:
- uncertainty estimates
- family/category variability
- case-level qualitative linkage
- release-grade artifact descriptions

## 2. Aggregate results are not enough

For mechanism papers, single-point rates are insufficient. Every major empirical claim should be supported by at least one of:
- bootstrap confidence intervals
- family-level or category-level variability
- case-level traces that explain how the metric arises

## 3. Scientific reasoning claims must stay governance-centered

The paper can use the phrase `bounded scientific reasoning` only if it simultaneously shows:
- condition governance
- abstention or qualification under unsupported conditions
- correction retention across later cases

It must also openly state when `scientific answering` remains weaker than `scientific claim governance`.

## 4. Figure 1 must be a mechanism figure

The main architecture figure should:
- show one readable control chain
- visually separate design envelope from validated subset
- avoid philosophy-coded labels
- avoid unreadable class-diagram side panels

The main figure should help a reviewer understand what was validated, not display the entire implementation universe.

## 5. Failure taxonomy must connect to examples

Counting failure types is useful only when the paper also shows:
- at least one representative direct-baseline failure
- at least one representative reflective over-deferral case
- at least one representative memory carryover case

Failure tables should not float free from concrete traces.

## 6. Availability language must describe a real review object

Avoid manuscript language that sounds like a future plan. Prefer:
- what artifacts already exist locally
- what the anonymized review package will contain
- what cannot yet be publicly exposed and why

## 7. Engineering tone is not enough

`Scientific tone` in the manuscript means:
- fewer declarations
- more evidence-linked interpretation
- more boundary conditions
- more explicit uncertainty
- less repeated slogan phrasing

## 8. Standing rule for future revisions

When a result looks unusually clean, the manuscript should proactively add:
- uncertainty interval
- benchmark boundary
- controlled-setting caveat

This is especially important for Track C-style memory results, where small sample sizes can otherwise look over-smoothed or over-claimed.
