# AGENTS.md

## Project identity
This repository implements a local prototype of a reflective metacognitive agent.
The goal is NOT to claim or simulate true subjective consciousness.
The goal IS to build a functional cognitive system with:
- structured self-monitoring
- internal critique
- long-term memory of errors and corrections
- controlled growth across tasks

## Core architecture
Treat the system as 4 layers:

1. Perception/Input Layer
   Receives user input, documents, observations, or task descriptions.

2. Cognition Layer
   Produces a structured candidate cognitive state rather than a direct final answer.

3. Mirror Layer
   Critiques the candidate state for:
   - premature convergence
   - concept blending
   - evidence gaps
   - hidden assumptions
   - overclaiming
   - old-template reuse
   - confusion between metacognition and subjective consciousness
   - confusion between wait-state and awareness itself

4. Seed Memory Layer
   Stores and retrieves:
   - facts
   - contexts
   - bias lineage
   - correction lineage
   - reusable strategies

## Non-goals
Do not frame the system as "proving AI consciousness".
Do not equate:
- self-monitoring with subjective experience
- wait states with awareness
- structured memory with human mind
Do not use philosophical analogy as engineering proof.

## Required core objects
Implement at minimum:
- MindState
- MirrorVerdict
- MemoryEpisode
- SelfState

Suggested fields:

MindState:
- current_input
- task_goal
- main_claim
- evidence
- hidden_assumptions
- alternative_paths
- confidence
- self_risk
- proposed_action
- self_state

MirrorVerdict:
- verdict: pass | revise | retrieve | wait | diverge
- issues
- guidance
- self_state_update

MemoryEpisode:
- input_summary
- context_tags
- claim
- evidence_summary
- bias_tags
- correction_actions
- final_result
- reusable_lessons

SelfState:
- stability
- uncertainty
- bias_risk
- attention_mode
- active_goal
- continuity_notes

## Coding requirements
- Prefer simple, modular Python first.
- Keep the architecture explicit and inspectable.
- Use dataclasses or pydantic models for core state.
- Separate orchestration from model adapters.
- Make memory backend swappable (JSON first, SQLite optional later).
- Include tests and sample runs.
- Log every cognition -> mirror -> revision transition.
- Avoid hidden chain-of-thought assumptions in code; store only structured summaries.

## Iteration strategy
Always work in this order:
1. define data models
2. build orchestrator loop
3. implement simple deterministic mirror rules
4. add model adapters
5. add memory persistence
6. add evaluation harness
7. only then explore creative/diverge mode

## Evaluation priorities
Optimize for:
- lower hallucination rate
- lower concept-mixing rate
- better explicit uncertainty handling
- better revision quality
- real effect of memory on later behavior

## When given a task
For non-trivial tasks:
1. inspect repository structure
2. propose a short plan
3. implement incrementally
4. run tests or demo script
5. summarize what changed
6. note open risks or missing parts

## Style
Be precise, restrained, and engineering-oriented.
Translate abstract cognitive language into:
- state variables
- system modules
- control flow
- validation procedures
