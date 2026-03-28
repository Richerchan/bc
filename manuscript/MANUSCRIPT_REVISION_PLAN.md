# Manuscript Revision Plan

Goal: move the current manuscript from a promising proof-of-mechanism draft to a submission-ready systems paper with bounded claims, clearer implementation boundaries, and a more defensible evidence chain.

## Priority Order

1. Tighten claims and remove self-judging language
2. Separate implemented components from planned components
3. Isolate novelty against closest baselines
4. Strengthen evaluation framing and artifact transparency
5. Reposition the paper as a reliability-control systems paper with scientific reasoning relevance, not as a broad AI4Science victory claim
6. Prepare the next experiment protocol for the science-facing benchmark

## Major Problems To Fix

1. Claim-evidence mismatch
The current title, abstract, and discussion still imply a broader scientific-reasoning contribution than the pilot benchmark can support.

2. Architecture-implementation mismatch
The system figure suggests a broad integrated platform, but the manuscript does not cleanly distinguish what is actually exercised in the current pilot.

3. Novelty isolation is weak
The manuscript says it is different from Self-Refine, Reflexion, CRITIC, and Self-RAG, but does not yet show this in a compact comparison table.

4. Evaluation is honest but still under-specified
The manuscript needs a clearer statement that the present results are proof-of-mechanism and a clearer protocol for the next benchmark stage.

5. Some wording still invites reviewer pushback
Sentences using "publishable" or overly self-certifying language should be removed.

## Table Plan

Table 1
Pilot benchmark summary
Status: done
Purpose: main aggregate result table

Table 2
Case-level outcomes
Status: done
Purpose: make mechanism-level changes legible

Table 3
Comparison to related reflective architectures
Status: add now
Purpose: isolate novelty on state externalization, typed control, correction-lineage memory, abstention governance, and implementation scope

Table 4
Implemented vs planned components
Status: add now
Purpose: resolve architecture-implementation ambiguity

Table 5
Planned science-facing benchmark protocol
Status: add now
Purpose: show a credible next experiment path with datasets, baselines, metrics, and expected evidence

## Execution Sequence

### Step 1: Claim tightening
- Remove self-judging phrases such as "publishable"
- Replace broad victory framing with "pilot evidence" and "proof-of-mechanism"
- Keep AI for Science relevance, but bound the conclusion

### Step 2: Boundary clarification
- Add a section explicitly distinguishing implemented and planned components
- Add a table mapping current modules, status, and whether they are exercised in the pilot

### Step 3: Novelty isolation
- Add a related-work comparison table against Self-Refine, Reflexion, CRITIC, and Self-RAG
- State clearly that the contribution is the combination of state externalization, verdict typing, and correction-lineage memory

### Step 4: Evaluation protocol strengthening
- Add a planned benchmark table with:
  - track
  - task family
  - baselines
  - metrics
  - artifact outputs
- Clarify that repeated deterministic runs demonstrate reproducibility, not statistical generalization

### Step 5: Final manuscript polish
- Unify terminology
- Keep philosophical analogy bounded
- Make the title, abstract, and conclusion mutually consistent

## What To Execute First

First execution batch:
- Step 1 claim tightening
- Step 2 boundary clarification
- Step 3 novelty isolation

Second execution batch:
- Step 4 evaluation protocol strengthening
- abstract and conclusion refinement

Third execution batch:
- final pass for title, terminology, references, and submission packaging
