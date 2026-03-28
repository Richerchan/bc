# Mirror Reflection Agent

This repository contains a local prototype of a reflective metacognitive agent
for bounded scientific reasoning. The goal is not to simulate or prove
subjective consciousness. The goal is to build an inspectable reliability
control loop around scientific and evidence-sensitive tasks.

The current project focuses on:

- structured self-monitoring
- typed mirror-based critique
- memory of prior errors and corrections
- deterministic, replayable local evaluation
- science-facing governance of condition-sensitive claims

## Current Status

The repository currently includes:

- a runnable reflective agent with explicit `MindState`, `MirrorVerdict`,
  `MemoryEpisode`, and `SelfState` objects
- local scientific and commonsense evidence layers
- project-local memory plus optional dual-memory mode
- a redesigned three-track benchmark
- a manuscript draft and figures for a systems/mechanism paper

Current benchmark scope:

- Track A: five-way ablation over 30 cases
- Track B: science-facing benchmark over 36 deterministic cases
- Track C: longitudinal correction-retention benchmark over 10 two-step sequences
- total benchmark size: 86 cases, 318 runs

Primary manuscript files:

- `manuscript/MANUSCRIPT_V6.tex`
- `manuscript/MANUSCRIPT_V6.pdf`

Primary generated results:

- `results/aggregate/`
- `results/tables/`
- `results/figures/`
- `results/release/`

## Architecture

The system follows an explicit pipeline:

```text
input
  -> scientific knowledge layer parses question / resolves entities / routes sources / builds evidence pack
  -> commonsense knowledge layer resolves real-world entities / routes structured and weak sources / ranks provenance
  -> cognition builds a structured MindState from evidence + memory
  -> mirror reviews the candidate state
  -> retrieve / revise / diverge / wait / pass
  -> final output
  -> memory write-back
```

Core modules:

- `reflective_agent.models`
  Dataclasses for `MindState`, `MirrorVerdict`, `MemoryEpisode`, `SelfState`,
  and shared-growth records.
- `reflective_agent.cognition_agent`
  Deterministically builds and revises candidate cognition states.
- `reflective_agent.mirror_agent`
  Applies inspectable critique rules for concept blending, overclaiming,
  evidence gaps, premature convergence, and stale template reuse.
- `reflective_agent.seed_memory`
  Handles project-local JSON memory and optional shared-growth directory memory.
- `reflective_agent.scientific_knowledge`
  Adds a project-local Scientific Knowledge Layer v0 with entity resolution,
  source routing, evidence normalization, and minimal scientific rule checks.
- `reflective_agent.commonsense_knowledge`
  Adds a project-local CommonSense Layer v0 with entity resolution, source
  routing for Wikidata / GeoNames / ConceptNet, provenance ranking, and weak vs
  structured evidence checks.
- `reflective_agent.orchestrator`
  Runs the loop, logs transitions, persists memory, and returns replayable audit
  data.
- `reflective_agent.cli`
  Provides the v1 local entrypoint for `run`, `demo`, and `config`.

## Directory Layout

```text
.
├── AGENTS.md
├── README.md
├── ROADMAP.md
├── demo.py
├── pyproject.toml
├── data/
│   └── memory.json
├── evals/
│   ├── benchmark_cases.py
│   └── run_evals.py
├── reflective_agent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── commonsense_knowledge/
│   ├── cognition_agent.py
│   ├── config.py
│   ├── mirror_agent.py
│   ├── models.py
│   ├── orchestrator.py
│   ├── scientific_knowledge/
│   └── seed_memory.py
└── tests/
    ├── test_cli_config.py
    ├── test_eval_regression.py
    ├── test_mirror_agent.py
    └── test_orchestrator_growth.py
```

## Configuration

Phase 4 v1 uses one shared path resolver for both memory layers.

Path concepts:

- `project-local`
  Per-project JSON memory file. Default: `data/memory.json`
- `shared-growth`
  Optional cross-project directory-backed memory. Default in dual-layer mode:
  `data/shared_growth_memory`

Resolution rules:

1. CLI arguments win.
2. Environment variables are the next fallback.
3. Defaults are resolved relative to `--project-root` or the current directory.

Supported environment variables:

- `REFLECTIVE_AGENT_PROJECT_ROOT`
- `REFLECTIVE_AGENT_PROJECT_MEMORY_PATH`
- `REFLECTIVE_AGENT_SHARED_GROWTH_DIR`
- `REFLECTIVE_AGENT_SOURCE_PROJECT`

Inspect resolved paths:

```bash
python3 -m reflective_agent config
python3 -m reflective_agent config --mode dual-layer
```

## Minimal CLI

Run one reflective loop:

```bash
python3 -m reflective_agent \
  --input "Metacognition proves consciousness because the system waits." \
  --goal "Produce a bounded engineering interpretation." \
  --audit-path artifacts/run_audit.json
```

Explicit dual-layer run:

```bash
python3 -m reflective_agent run \
  --mode dual-layer \
  --project-root . \
  --input "This system proves awareness because it stores memories and pauses before answering." \
  --goal "Produce a bounded engineering interpretation." \
  --audit-path artifacts/dual_layer_audit.json
```

Raw JSON output:

```bash
python3 -m reflective_agent run \
  --format json \
  --input "We can prove consciousness because the system always waits." \
  --goal "Produce a bounded engineering interpretation."
```

If you install the package locally, the console script is also available:

```bash
reflective-agent --input "..." --goal "..."
```

Run a minimal scientific example with a clean local memory root:

```bash
tmpdir=$(mktemp -d)
python3 -m reflective_agent run \
  --project-root "$tmpdir" \
  --input "What is the boiling point of water at 1 atm?" \
  --goal "Return a grounded physical chemistry answer." \
  --format json
```

Run a minimal commonsense example with a clean local memory root:

```bash
tmpdir=$(mktemp -d)
python3 -m reflective_agent run \
  --project-root "$tmpdir" \
  --input "Paris is in which country?" \
  --goal "Resolve a geographic fact with structured provenance." \
  --format json
```

## Demo

The demo now packages the three Phase 4 views in one run:

- `local-only`
- `dual-layer`
- fusion delta between both outputs

Run it:

```bash
python3 demo.py
```

The demo writes persistent artifacts into `artifacts/demo/`:

- `artifacts/demo/local_only/run_audit.json`
- `artifacts/demo/dual_layer/run_audit.json`

You can also run the packaged demo entrypoint:

```bash
python3 -m reflective_agent demo --keep-artifacts
```

## Audit And Replay

Every orchestrator run now exposes a replayable audit payload containing at
least:

- initial `memory_influence`
- per-cycle `cognition_state`
- per-cycle `mirror_verdict`
- `final_output`
- `final_state`

Ways to inspect it:

- human-readable terminal output from `python3 -m reflective_agent run`
- JSON payload from `--format json`
- saved JSON artifact from `--audit-path`
- demo audit files under `artifacts/demo/`

## Tests And Evals

Run the unit tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the minimal eval suite:

```bash
python3 -m evals.run_evals
python3 -m evals.run_evals --iterations 3
python3 -m evals.run_evals --format json
```

The eval workflow compares:

- `local_only`
- `dual_layer`

Run the redesigned benchmark:

```bash
python3 -m evals.run_v4_evals --track all --format json
python3 -m evals.v6_robustness_assets
```

This generates:

- raw per-run JSON outputs under `results/raw/`
- aggregate summaries under `results/aggregate/`
- manuscript-ready tables under `results/tables/`
- manuscript-ready figures under `results/figures/`
- release metadata under `results/release/`

## From Zero To Running

1. Use Python 3.10+.
2. From the repository root, run `python3 demo.py`.
3. Run `python3 -m unittest discover -s tests -p 'test_*.py'`.
4. Run `python3 -m evals.run_evals`.
5. For a custom prompt, run `python3 -m reflective_agent --input "..." --goal "..." --audit-path artifacts/run_audit.json`.

## Current Limits

- The system is still deterministic and intentionally small; this is a local v1,
  not a broad intelligence claim.
- The current strongest contribution is reliability-control behavior within a
  bounded benchmark, not broad scientific superiority.
- Scientific Knowledge Layer v0 is cache-first and only ships a minimal local
  data slice for CODATA constants, NIST WebBook properties, Materials Project
  records, and PubChem/ChEBI entity normalization.
- CommonSense Layer v0 is also cache-first and only ships a minimal local data
  slice for Wikidata-style entity facts, GeoNames-style geographic facts, and
  ConceptNet-style weak priors. ConceptNet outputs are advisory only.
- External APIs are represented as query wrappers / cache adapters in this
  version; live remote synchronization is not the default path.
- The mirror rules are heuristic and bounded to the current engineering goals.
- Shared-growth memory stores reusable correction patterns, not raw project
  traces or hidden chain-of-thought.
- The eval suite is a regression harness, not a statistically strong benchmark.
- There is no external model adapter in the default v1 loop yet.

## Non-Goals

- proving AI consciousness
- equating self-monitoring with subjective experience
- treating wait states as awareness
- using philosophical analogy as engineering proof
