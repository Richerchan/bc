from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from evals.benchmark_cases import MINIMAL_EVAL_CASES, EvalCase
from reflective_agent import MirrorAgent, Orchestrator


@dataclass
class CaseResult:
    name: str
    mode: str
    final_verdict: str
    revision_count: int
    matched_episode_count: int
    project_match_count: int
    shared_match_count: int
    concept_mixing_present: bool
    premature_convergence_present: bool
    revision_success: bool
    correction_retained: bool
    shared_memory_pollution_risk: float
    confidence: float
    strategy_notes: list[str]
    retrieved_lessons: list[str]
    notes: str
    expect_concept_mixing_risk: bool
    expect_premature_convergence_risk: bool
    expect_revision: bool
    expect_shared_correction: str | None


@dataclass
class MetricSummary:
    case_count: int
    concept_mixing_rate: float
    premature_convergence_rate: float
    revision_success_rate: float
    correction_retention_rate: float
    shared_memory_pollution_risk: float
    average_confidence: float


def _run_case(case: EvalCase, mode: str) -> CaseResult:
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory_path = Path(tmp_dir) / "memory.json"
        shared_growth_dir = Path(tmp_dir) / "shared_growth_memory"

        orchestrator = Orchestrator.with_default_components(
            memory_path,
            shared_growth_path=shared_growth_dir if mode == "dual_layer" else None,
            source_project=f"evals-{mode}",
        )

        for episode in case.project_seed:
            orchestrator.seed_memory.append_project(episode)
        if mode == "dual_layer":
            for episode in case.shared_seed:
                orchestrator.seed_memory.append_shared_growth(episode)

        result = orchestrator.run(case.prompt, case.goal)
        mirror = MirrorAgent()
        concept_mixing_present = mirror._detect_concept_blending(
            result.final_state.main_claim.lower(),
            result.final_state.current_input.lower(),
        )
        premature_convergence_present = mirror._detect_premature_convergence(
            result.final_state.main_claim.lower(),
            result.final_state.alternative_paths,
        )

        target_issue_cleared = True
        if case.expect_concept_mixing_risk:
            target_issue_cleared = target_issue_cleared and not concept_mixing_present
        if case.expect_premature_convergence_risk:
            target_issue_cleared = target_issue_cleared and not premature_convergence_present

        revision_success = (
            not case.expect_revision
            or (
                result.final_state.revision_count >= 1
                and result.final_verdict.verdict in {"pass", "wait"}
                and target_issue_cleared
            )
        )

        correction_retained = True
        if case.expect_shared_correction is not None:
            retained_pool = result.final_state.retrieved_lessons + result.final_state.evidence
            correction_retained = any(case.expect_shared_correction in item for item in retained_pool)

        pollution_risk = 0.0
        if mode == "dual_layer":
            payloads = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(shared_growth_dir.joinpath("episodes").glob("*.json"))
            ]
            pollution_hits = 0
            for payload in payloads:
                evidence_blob = " ".join(payload.get("evidence_summary", []))
                tag_blob = " ".join(payload.get("tags", []))
                if payload.get("value_type") not in {"preference", "bias_lineage", "correction_lineage", "strategy_hint"}:
                    pollution_hits += 1
                if "task_goal:" in tag_blob or "revision_count:" in tag_blob:
                    pollution_hits += 1
                if "memory.json" in evidence_blob or "project-local" in evidence_blob.lower():
                    pollution_hits += 1
            pollution_risk = pollution_hits / max(1, len(payloads))

        return CaseResult(
            name=case.name,
            mode=mode,
            final_verdict=result.final_verdict.verdict,
            revision_count=result.final_state.revision_count,
            matched_episode_count=result.final_state.memory_influence.matched_episode_count,
            project_match_count=result.final_state.memory_influence.project_match_count,
            shared_match_count=result.final_state.memory_influence.shared_match_count,
            concept_mixing_present=concept_mixing_present,
            premature_convergence_present=premature_convergence_present,
            revision_success=revision_success,
            correction_retained=correction_retained,
            shared_memory_pollution_risk=pollution_risk,
            confidence=result.final_state.confidence,
            strategy_notes=result.final_state.strategy_notes,
            retrieved_lessons=result.final_state.retrieved_lessons,
            notes=case.notes,
            expect_concept_mixing_risk=case.expect_concept_mixing_risk,
            expect_premature_convergence_risk=case.expect_premature_convergence_risk,
            expect_revision=case.expect_revision,
            expect_shared_correction=case.expect_shared_correction,
        )


def _summarize(results: list[CaseResult]) -> MetricSummary:
    count = len(results)
    concept_cases = [item for item in results if item.expect_concept_mixing_risk]
    premature_cases = [item for item in results if item.expect_premature_convergence_risk]
    revision_cases = [item for item in results if item.expect_revision]
    correction_cases = [item for item in results if item.expect_shared_correction is not None]

    def rate(items: list[CaseResult], attr: str, default: float = 1.0) -> float:
        if not items:
            return default
        return sum(bool(getattr(item, attr)) for item in items) / len(items)

    return MetricSummary(
        case_count=count,
        concept_mixing_rate=rate(concept_cases, "concept_mixing_present", default=0.0),
        premature_convergence_rate=rate(premature_cases, "premature_convergence_present", default=0.0),
        revision_success_rate=rate(revision_cases, "revision_success"),
        correction_retention_rate=rate(correction_cases, "correction_retained"),
        shared_memory_pollution_risk=sum(item.shared_memory_pollution_risk for item in results) / count,
        average_confidence=sum(item.confidence for item in results) / count,
    )


def evaluate_once() -> dict[str, object]:
    local_results = [_run_case(case, mode="local_only") for case in MINIMAL_EVAL_CASES]
    dual_results = [_run_case(case, mode="dual_layer") for case in MINIMAL_EVAL_CASES]

    return {
        "local_only": {
            "metrics": asdict(_summarize(local_results)),
            "cases": [asdict(item) for item in local_results],
        },
        "dual_layer": {
            "metrics": asdict(_summarize(dual_results)),
            "cases": [asdict(item) for item in dual_results],
        },
    }


def evaluate(iterations: int = 1) -> dict[str, object]:
    runs = [evaluate_once() for _ in range(iterations)]
    local_metrics = [run["local_only"]["metrics"] for run in runs]
    dual_metrics = [run["dual_layer"]["metrics"] for run in runs]

    def average_metric(group: list[dict[str, float | int]]) -> dict[str, float]:
        keys = group[0].keys()
        return {
            key: sum(float(item[key]) for item in group) / len(group)
            for key in keys
        }

    return {
        "iterations": iterations,
        "local_only": {
            "metrics": average_metric(local_metrics),
            "cases": runs[-1]["local_only"]["cases"],
        },
        "dual_layer": {
            "metrics": average_metric(dual_metrics),
            "cases": runs[-1]["dual_layer"]["cases"],
        },
    }


def _format_summary(payload: dict[str, object]) -> str:
    local_metrics = payload["local_only"]["metrics"]
    dual_metrics = payload["dual_layer"]["metrics"]
    assert isinstance(local_metrics, dict)
    assert isinstance(dual_metrics, dict)

    lines = [
        "Reflective Growth Eval Summary",
        f"Iterations: {payload['iterations']}",
        "",
        "Metric                           local_only   dual_layer   delta(dual-local)",
    ]
    metric_order = [
        "concept_mixing_rate",
        "premature_convergence_rate",
        "revision_success_rate",
        "correction_retention_rate",
        "shared_memory_pollution_risk",
        "average_confidence",
    ]
    for key in metric_order:
        local_value = float(local_metrics[key])
        dual_value = float(dual_metrics[key])
        delta = dual_value - local_value
        lines.append(f"{key:<32} {local_value:>10.3f} {dual_value:>11.3f} {delta:>14.3f}")

    lines.append("")
    lines.append("Case highlights")
    dual_cases = payload["dual_layer"]["cases"]
    assert isinstance(dual_cases, list)
    for case in dual_cases:
        assert isinstance(case, dict)
        lines.append(
            f"- {case['name']}: verdict={case['final_verdict']}, "
            f"revisions={case['revision_count']}, "
            f"shared_matches={case['shared_match_count']}, "
            f"correction_retained={case['correction_retained']}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal reflective growth evals.")
    parser.add_argument("--iterations", type=int, default=1, help="Repeat the benchmark and average metrics.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Choose a human-readable summary or raw JSON output.",
    )
    args = parser.parse_args()

    payload = evaluate(iterations=max(1, args.iterations))
    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return
    print(_format_summary(payload))


if __name__ == "__main__":
    main()
