# Mirror Reflection Agent: Structured Reliability Control for Scientific Reasoning

Working version: submission-oriented draft with bounded claims.

## Title Candidates

1. Mirror Reflection Agent: Structured Reliability Control for Scientific Reasoning
2. A Mirror Reflection Agent for Reliable Scientific QA with Typed Critique and Correction Lineage
3. Structured Reflective Control for Scientific Reasoning with Explicit Memory and Abstention

## Abstract

Large language models are increasingly used in scientific workflows, but their practical value is limited by unsupported certainty, weak handling of evidence conditions, and poor retention of prior corrections. We present Mirror Reflection Agent, a reliability-oriented architecture that separates candidate cognition from final output and inserts an explicit mirror-critique stage between them. The system constructs a structured intermediate state, critiques it with typed verdicts such as revise, retrieve, wait, diverge, and pass, and stores correction lineage and reusable strategy signals in memory. Unlike generic self-refinement pipelines, the proposed architecture externalizes intermediate cognition and makes revision control auditable. We instantiate the design with scientific and commonsense knowledge layers, a deterministic critique module, project-local memory, and replayable run audits. We argue that the key contribution is not a claim about consciousness or subjective awareness, but a practical control mechanism for safer reasoning. The paper positions the architecture as a reliability method for AI for Science, especially in tasks where evidence provenance, uncertainty, and abstention matter as much as answer accuracy. We outline an experimental program that can be executed by a solo researcher using a small benchmark suite, lightweight open models, and API-based baselines, focusing on hallucination reduction, revision quality, correction retention, and bounded abstention.

## 1. Introduction

Scientific use of large language models requires more than fluent answers. A useful system must distinguish strong evidence from weak prior knowledge, preserve source conditions, reduce unsupported certainty, and remember prior corrections without blindly repeating them. Existing agent pipelines often improve outputs by adding reflection or retrieval, but they still leave three recurring problems:

- intermediate reasoning is not represented as an inspectable object
- critique outcomes are not encoded as explicit control decisions
- prior corrections are not preserved as structured reusable lineage

This paper addresses those gaps with Mirror Reflection Agent, a structured reliability-control architecture. Rather than directly producing a final answer, the system builds a candidate cognitive state, critiques it with a mirror layer, and then either revises, retrieves memory, diverges to a new scaffold, defers, or finalizes. The design is engineering-oriented and auditable. It does not claim subjective awareness, consciousness, or human-like introspection.

Our central claim is narrow and testable: explicit cognitive state plus typed critique plus correction-lineage memory can improve reliability in scientific and science-adjacent reasoning tasks.

## 2. Core Contribution

The deepest contribution of the architecture is not generic self-reflection. It is the conversion of reliability problems into explicit state and explicit control flow.

The architecture contributes three linked mechanisms:

1. State externalization
   Candidate reasoning is represented as a structured `MindState` with claim, evidence, assumptions, alternatives, confidence, and risk.

2. Verdict-typed oversight
   Critique is represented as a structured `MirrorVerdict` with explicit actions: `pass`, `revise`, `retrieve`, `wait`, and `diverge`.

3. Correction-lineage memory
   Memory stores not only facts, but also prior bias alerts, correction actions, and reusable strategies.

This makes the system materially different from prompt-only reflection. The mirror is not just another text prompt. It is a decision layer that governs whether the system should answer, revise, retrieve, or abstain.

## 3. Architecture

The system follows:

`input -> knowledge layers -> cognition -> mirror critique -> revise/retrieve/diverge/wait/pass -> output -> memory write-back`

Figure 1 should appear at the start of this section as the overall system diagram. The existing engineering schematic is the right high-level entry point because it shows the relation between knowledge layers, cognition, mirror verdicts, and memory influence.

### 3.1 Scientific Knowledge Layer

The scientific layer is responsible for higher-confidence, condition-sensitive evidence. Its role is to:

- parse scientific entity/property questions
- resolve entities and normalize units
- route across structured scientific sources
- build evidence packs with provenance and warnings

This layer is the source of hard constraints.

### 3.2 Commonsense Knowledge Layer

The commonsense layer is responsible for softer background priors. Its role is to:

- resolve general entities and relations
- provide context when prompts rely on implicit world knowledge
- distinguish structured facts from weak commonsense priors

This layer should not be treated as equivalent to scientific evidence. Its proper role is contextual support, not unrestricted claim justification.

### 3.3 Cognition Layer

The cognition layer builds a structured `MindState` containing:

- current input
- task goal
- main claim
- evidence
- hidden assumptions
- alternative paths
- confidence
- self-risk
- proposed action
- self-state

This step externalizes an otherwise opaque intermediate draft.

### 3.4 Mirror Layer

The mirror layer reviews the `MindState` and returns a `MirrorVerdict`.

Current implemented checks include:

- premature convergence
- concept blending
- evidence gap
- overclaiming
- weak commonsense presented as fact
- structured-fact priority violation
- unit inconsistency
- condition-scope violations
- stale template reuse
- divergence need

The mirror is best understood as a reliability governor.

### 3.5 Memory Layer

The memory layer contains project-local memory and optional shared-growth memory. The key memory signals are:

- fact hints
- context hints
- bias alerts
- correction hints
- strategy hints
- divergence triggers

This gives the architecture a notion of bounded continuity across runs.

## 4. Why This Architecture Matters

The architecture addresses several practical problems in current LLM agents.

### 4.1 It separates knowledge types by epistemic role

Scientific evidence and commonsense priors should not have equal authority. The architecture makes that distinction explicit and allows the mirror layer to prevent weak priors from being promoted into factual claims.

### 4.2 It treats abstention as a first-class outcome

In scientific settings, refusing or deferring can be safer than answering. The `wait` verdict supports bounded abstention when evidence is insufficient or inconsistent.

### 4.3 It supports cumulative correction

Most systems retrieve facts but do not retrieve prior mistakes as reusable constraints. Here, prior corrections become structured signals that can influence later behavior.

### 4.4 It is auditable

Each run produces replayable audit information showing memory influence, cognition state, mirror verdicts, and final output.

## 5. What This Architecture Is Not

The paper should explicitly reject several overstatements.

- It is not a consciousness model.
- It is not evidence of subjective awareness.
- It is not an autonomous scientist.
- It is not a general solution to continual learning.

The architecture supports bounded reliability improvement under explicit control. That is already a meaningful contribution.

## 6. Current Blind Spots

The present system still has important limitations.

### 6.1 No strong long-horizon growth

The agent can reuse corrections, but it does not autonomously redesign its own rules, objectives, or schema. That is controlled adaptation, not full self-improvement.

### 6.2 Limited dialogue accumulation

The memory system preserves structured lessons, but it does not yet maintain rich multi-session dialogue continuity with evolving user preferences, conceptual drift, and conflict resolution.

### 6.3 Incomplete critique coverage

The mirror works well on explicit risks such as overclaiming or evidence gaps, but may still miss subtle errors in decomposition, framing, or hidden variable choice.

### 6.4 Stronger at reliability than discovery

The current system is better positioned for reliable scientific QA and bounded explanation than for open-ended hypothesis generation.

## 7. Experimental Direction for a Solo Researcher

The experimental plan should be designed for limited compute.

### 7.1 Main principle

Do not try to beat frontier models on absolute science ability. Instead, show that the architecture improves reliability properties under practical resource constraints.

### 7.2 Three-track evaluation

Track A: Internal reliability benchmark

- concept blending cases
- premature convergence cases
- correction retention cases
- memory pollution cases
- bounded control cases

Track B: Small scientific QA benchmark

- 100 to 300 manually curated questions
- chemistry, materials, physical constants, unit-sensitive queries
- answers backed by structured sources already close to the current implementation

Track C: Longitudinal correction benchmark

- families of related prompts across sessions
- repeated mistakes with corrected variants
- tests whether prior corrections are retrieved, applied, ignored, or overgeneralized

### 7.3 Feasible baselines

The following baselines are realistic without major infrastructure:

1. Direct answer baseline
2. Structured cognition without mirror
3. Mirror without memory
4. Mirror plus local memory
5. Mirror plus dual-layer memory

Optional API baselines can be added selectively for comparison, but the core paper should remain executable on modest resources.

### 7.4 Models and compute

A solo-researcher-friendly setup could use:

- local 7B to 14B instruction-tuned open models for repeatable runs
- rented single-GPU cloud instances only for batch experiments
- API models only for a small comparison slice, not the entire study

The key is to keep the benchmark size and evaluation loop small enough to rerun after each revision.

### 7.5 Metrics

Primary metrics:

- answer correctness
- hallucination rate
- concept-mixing rate
- unsupported-certainty rate
- revision success rate
- correction retention rate
- abstention quality
- unit-consistency rate
- condition-scope preservation rate

Secondary metrics:

- average number of revisions
- average confidence
- retrieval hit rate
- memory pollution risk

## 8. Experimental Results From The Current Implementation

We ran the existing project benchmark directly from the repository without changing code:

`python3 -m evals.run_evals --format json`

This benchmark currently contains four cases and compares `local_only` against `dual_layer`. Even though it is still small, it already shows the intended architectural effect.

### 8.1 Metric Summary

- `premature_convergence_rate`: local-only `1.000`, dual-layer `0.000`
- `revision_success_rate`: local-only `0.500`, dual-layer `1.000`
- `correction_retention_rate`: local-only `0.000`, dual-layer `1.000`
- `shared_memory_pollution_risk`: local-only `0.000`, dual-layer `0.000`
- `average_confidence`: local-only `0.6075`, dual-layer `0.5625`

The pattern is encouraging. Dual-layer memory lowers over-assertive convergence, improves revision success, and preserves prior corrections while keeping pollution risk at zero. The drop in average confidence is desirable in this setting because the stronger condition is not maximal confidence, but better calibrated bounded behavior.

### 8.2 Case-Level Interpretation

- In `concept_blending_shared_recovery`, dual-layer memory retained the target correction while local-only did not.
- In `premature_convergence_shared_bias_alert`, dual-layer memory removed premature convergence and preserved the shared correction signal.
- In `project_local_precedence`, the system preserved project-local strategy priority while still using shared memory as advisory context.
- In `bounded_control_case`, dual-layer memory did not degrade already-good behavior.

### 8.3 What These Results Demonstrate

These results do not prove broad scientific superiority. They demonstrate a narrower and more credible point: the architecture improves reliability-oriented behavior under correction and memory. This is the right level of claim for the current paper.

### 8.4 Files Produced

- Raw benchmark output: `manuscript/rawdata.txt`
- Plot summarizing key metrics: `manuscript/experiment_summary.png`

The raw file should be included in supplementary materials or repository artifacts. The PNG can be used as an early paper figure for the benchmark section.

## 9. Journal Strategy

### 8.1 Recommended primary target

`Machine Learning: Science and Technology`

Reason:

- explicitly welcomes methodological advances in machine learning motivated by scientific problems
- a good fit for "reliability architecture for scientific reasoning"
- more realistic than top-tier glamour venues for a solo researcher

### 8.2 Recommended fallback or parallel-fit journals

`Frontiers in Artificial Intelligence`

- suitable for agent reliability, reasoning, and practical AI systems
- broad enough to accommodate architecture plus evaluation

`npj Artificial Intelligence`

- attractive if the experiments become stronger and the narrative is sharpened
- more selective, so likely a stretch target rather than first submission

`Communications AI & Computing`

- relevant if the final story emphasizes interpretable AI, reasoning, and multi-agent or oversight structure
- also more selective than the first two options

### 8.3 Positioning sentence for editors

This paper presents a structured reliability-control architecture for scientific reasoning with explicit intermediate state, typed critique decisions, and correction-lineage memory, together with a lightweight but reproducible evaluation protocol focused on bounded reliability rather than raw scale.

## 10. Practical Next Steps

1. Freeze the core claim around reliability control.
2. Remove all language suggesting consciousness or strong autonomy.
3. Build a compact benchmark that can be rerun cheaply.
4. Add one ablation table and one longitudinal correction table.
5. Submit first to a methods-friendly journal.

## 11. Limitations

The current prototype does not yet demonstrate:

- strong continual learning
- robust multi-session conversational identity
- broad scientific discovery ability
- comprehensive critique coverage for all failure modes

These limits should remain explicit in the manuscript.

## References To Prioritize

- Self-Refine
- Reflexion
- CRITIC
- Self-RAG
- GPQA
- scalable oversight work on weak judges and strong models
- selective or abstaining QA where relevant
