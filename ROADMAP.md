# Roadmap

## Phase 1

- Define inspectable state objects for cognition, mirror verdicts, memory, and self-state.
- Build a deterministic cognition -> mirror -> revise/retrieve/wait/pass loop.
- Persist structured memory episodes locally.

## Phase 2

- Split memory into facts, contexts, bias lineage, correction lineage, and reusable strategies.
- Let retrieval alter the next run's confidence, assumptions, and strategy notes.
- Add diverge mode when prior patterns become too repetitive.

## Phase 3

- Expand the eval harness with richer benchmark sets and saved reports.
- Add a swappable SQLite backend beside JSON.
- Introduce model adapters behind the same structured state contract.

## Phase 4

- Add batch simulations for long-horizon continuity tests.
- Track growth over time: repeated errors, recovery speed, and strategy reuse quality.
- Explore a human-auditable dashboard for traces, memory entries, and lineage views.
