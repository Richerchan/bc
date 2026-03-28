# Memory Iteration: npj Comparison V1

Source anchor:
- `Self-reflection enhances large language models towards substantial academic response`

## What to remember

The overlap in vocabulary (`reflection`, `memory`, `bank`) is not the overlap that matters. The published npj paper optimizes language generation for academic response writing. Our manuscript targets bounded scientific reasoning under local evidence constraints. The comparison should therefore be framed as a difference in problem class, control structure, and memory semantics, not as a race over who uses reflection first.

## Stable differentiation points

1. Their reflection improves relevance and rhetorical adequacy in response writing. Ours governs factual boundaries, condition preservation, abstention, and correction reuse in scientific settings.
2. Their reflection bank stores reusable response experience. Our correction-lineage memory stores factual boundary lessons, prior failures, and reusable constraint traces.
3. Their setting is broad language assistance. Our setting is deterministic, locally auditable, and suitable for privacy-sensitive or resource-constrained scientific use.
4. Their strongest evidence comes from scale and broad data coverage. Our strongest evidence comes from explicit control structure, deterministic scoring, and auditable behavior change.

## Writing rules derived from the comparison

- Do not compete on generic `self-reflection` rhetoric.
- Emphasize `typed control`, `condition preservation`, `unsupported extrapolation`, and `local evidence traceability`.
- When discussing memory, avoid generic phrases such as `better reuse of reflections`. Prefer `correction lineage`, `boundary knowledge`, and `constraint reuse`.
- When discussing local deployment, connect it to scientific auditability and unpublished-data protection, not to generic edge-AI marketing.

## Experiment framing rules derived from the comparison

- Track A should remain the architectural anchor because it isolates control-structure gains.
- Track B should emphasize two things simultaneously:
  - the system is already better at refusing unsupported extrapolation;
  - it is not yet good enough at calibrated conditioned answering.
- Track C should be framed as evidence that remembered corrections can function as scientific constraint carryover, not only as dialogue continuity.

## Next upgrade targets

1. Add a stronger discussion sentence that the current benchmark demonstrates safer factual boundary behavior, not broader scientific competence.
2. In future benchmark expansion, prioritize harder condition-sensitive scientific cases rather than more generic QA.
3. When adding related work, compare against reflection-for-writing and reflection-for-retrieval as adjacent but distinct families.
