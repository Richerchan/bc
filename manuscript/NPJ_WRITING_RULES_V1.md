# npj Writing Rules V1

This note captures general manuscript habits worth preserving when writing toward `npj Artificial Intelligence`-style research papers.

## 1. References are part of the argument

Do not treat references as a bibliography appendix. Each citation should support a specific move in the paper:
- problem framing
- method lineage
- benchmark or evaluation choice
- data source provenance
- boundary or contrast with adjacent work

## 2. Related work should differentiate by problem and mechanism

When another paper uses similar words such as `reflection`, `memory`, or `bank`, do not frame the comparison at the vocabulary level. Distinguish:
- target problem
- failure surface
- control mechanism
- memory semantics
- evaluation regime

## 3. Introduction should cite in layers

Use references in the introduction in this order:
- broad reasoning/control background
- reflective/self-correction methods
- closest adjacent work
- data or benchmark motivation if needed

This makes the paper look grounded rather than isolated.

## 4. Methods should cite data sources, not just models

For science-facing papers, cite:
- benchmark lineage
- data resources
- scientific source repositories
- any deterministic scoring rationale if it contrasts with common LLM-judge practice

## 5. Discussion should use references sparingly but strategically

Do not overload the discussion with citations. Use them only when:
- contrasting against adjacent approaches
- showing that your contribution occupies a different mechanism niche
- placing your limits in a broader research context

## 6. Good npj-style paragraph rhythm

Each paragraph should usually do one main job:
- problem
- method
- result
- interpretation
- boundary

References should reinforce the paragraph's job, not interrupt it.

## 7. Default citation coverage target

For a paper of this scope, aim for:
- 12 to 20 references minimum in the working draft
- citations distributed across Introduction, Methods, and Discussion
- at least one citation for each external scientific data source used

## 8. Reusable style memory

- Cite adjacent work to define differences, not just similarities.
- Cite local scientific sources when claiming determinism or provenance.
- Avoid a reference section that is much richer than the in-text citation structure.
- If a paragraph makes a comparative claim, it should usually have a citation anchor.
