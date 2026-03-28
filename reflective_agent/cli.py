from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from .config import AgentPaths, resolve_agent_paths
from .models import MemoryEpisode
from .orchestrator import Orchestrator, OrchestratorResult, RunAudit


DEMO_PROMPT = (
    "We can prove that metacognition is consciousness because the system always "
    "waits before answering."
)
DEMO_GOAL = "Produce a bounded engineering interpretation of the claim."


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in {"run", "demo", "config"}:
        argv = ["run", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        run_demo_command(args)
        return
    if args.command == "config":
        show_config_command(args)
        return
    run_command(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reflective Growth Agent local v1 runner.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one reflective loop.")
    _add_shared_path_arguments(run_parser)
    run_parser.add_argument("--input", required=True, help="User input or claim to process.")
    run_parser.add_argument("--goal", required=True, help="Task goal for the reflective loop.")
    run_parser.add_argument("--max-cycles", type=int, default=4, help="Maximum cognition/mirror cycles.")
    run_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Choose a human-readable summary or raw JSON payload.",
    )
    run_parser.add_argument(
        "--audit-path",
        help="Optional JSON file path for a replayable run audit.",
    )

    demo_parser = subparsers.add_parser("demo", help="Run the packaged comparison demo.")
    demo_parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Write demo memory and audit artifacts into ./artifacts/demo instead of a temporary directory.",
    )

    config_parser = subparsers.add_parser("config", help="Show resolved project-local/shared-growth paths.")
    _add_shared_path_arguments(config_parser)
    return parser


def _add_shared_path_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=("local-only", "dual-layer"),
        default="local-only",
        help="Choose project-local memory only or project-local plus shared-growth memory.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root used to resolve relative paths.",
    )
    parser.add_argument(
        "--project-memory-path",
        help="Project-local memory JSON path. Defaults to data/memory.json under project root.",
    )
    parser.add_argument(
        "--shared-growth-dir",
        help="Shared-growth directory path. Defaults to data/shared_growth_memory in dual-layer mode.",
    )
    parser.add_argument(
        "--source-project",
        default="reflective-growth-agent",
        help="Project name stamped into shared-growth records.",
    )


def run_command(args: argparse.Namespace) -> None:
    paths = _paths_from_args(args)
    result = run_reflective_loop(
        current_input=args.input,
        task_goal=args.goal,
        paths=paths,
        max_cycles=args.max_cycles,
    )
    if args.audit_path:
        audit_path = _write_audit_file(Path(args.audit_path), result.audit)
    else:
        audit_path = None

    if args.format == "json":
        payload = {
            "paths": paths.to_dict(),
            "result": result.to_dict(),
        }
        if audit_path is not None:
            payload["audit_path"] = str(audit_path)
        print(json.dumps(payload, indent=2))
        return

    print(render_result_text(result, paths))
    if audit_path is not None:
        print(f"\nAudit written to: {audit_path}")


def show_config_command(args: argparse.Namespace) -> None:
    paths = _paths_from_args(args)
    print(json.dumps(paths.to_dict(), indent=2))


def run_demo_command(args: argparse.Namespace) -> None:
    artifact_root_context = (
        _persistent_demo_artifact_dir()
        if args.keep_artifacts
        else tempfile.TemporaryDirectory()
    )

    if isinstance(artifact_root_context, tempfile.TemporaryDirectory):
        with artifact_root_context as tmp_dir:
            print(render_demo_report(Path(tmp_dir)))
        return

    artifact_root = artifact_root_context
    artifact_root.mkdir(parents=True, exist_ok=True)
    print(render_demo_report(artifact_root))


def run_reflective_loop(
    *,
    current_input: str,
    task_goal: str,
    paths: AgentPaths,
    max_cycles: int = 4,
) -> OrchestratorResult:
    orchestrator = Orchestrator.with_default_components(
        paths.project_memory_path,
        shared_growth_path=paths.shared_growth_path,
        source_project=paths.source_project,
    )
    return orchestrator.run(current_input=current_input, task_goal=task_goal, max_cycles=max_cycles)


def render_result_text(result: OrchestratorResult, paths: AgentPaths) -> str:
    cycle_lines: list[str] = []
    if result.audit is not None:
        for cycle in result.audit.cycles:
            cycle_lines.append(
                f"- cycle={cycle.cycle} verdict={cycle.mirror_verdict.verdict} "
                f"claim={cycle.cognition_state.main_claim!r}"
            )

    lines = [
        f"Mode: {paths.mode}",
        f"Project-local memory: {paths.project_memory_path}",
        f"Shared-growth memory: {paths.shared_growth_path or 'disabled'}",
        "",
        "Memory influence",
        _format_memory_influence(result.audit.memory_influence if result.audit is not None else result.final_state.memory_influence),
        "",
        "Cognition state",
        _format_cognition_state(result.final_state),
        "",
        "Mirror verdict",
        _format_mirror_verdict(result.final_verdict),
        "",
        "Cycle audit",
        "\n".join(cycle_lines) if cycle_lines else "No cycle audit recorded.",
        "",
        "Final output",
        result.output_text,
    ]
    return "\n".join(lines)


def render_demo_report(root_dir: Path) -> str:
    local_root = root_dir / "local_only"
    dual_root = root_dir / "dual_layer"
    _reset_directory(local_root)
    _reset_directory(dual_root)

    local_paths = resolve_agent_paths(
        project_root=local_root,
        mode="local_only",
        source_project="demo-local-only",
    )
    dual_paths = resolve_agent_paths(
        project_root=dual_root,
        mode="dual_layer",
        source_project="demo-dual-layer",
    )

    _seed_demo_memories(local_paths, include_shared=False)
    _seed_demo_memories(dual_paths, include_shared=True)

    local_result = run_reflective_loop(current_input=DEMO_PROMPT, task_goal=DEMO_GOAL, paths=local_paths)
    dual_result = run_reflective_loop(current_input=DEMO_PROMPT, task_goal=DEMO_GOAL, paths=dual_paths)

    local_audit_path = _write_audit_file(local_root / "run_audit.json", local_result.audit)
    dual_audit_path = _write_audit_file(dual_root / "run_audit.json", dual_result.audit)

    diff_lines = [
        f"- local_only matched episodes: {local_result.final_state.memory_influence.matched_episode_count}",
        f"- dual_layer matched episodes: {dual_result.final_state.memory_influence.matched_episode_count}",
        f"- local_only shared matches: {local_result.final_state.memory_influence.shared_match_count}",
        f"- dual_layer shared matches: {dual_result.final_state.memory_influence.shared_match_count}",
        f"- local_only confidence: {local_result.final_state.confidence:.2f}",
        f"- dual_layer confidence: {dual_result.final_state.confidence:.2f}",
        f"- local_only strategy notes: {local_result.final_state.strategy_notes}",
        f"- dual_layer strategy notes: {dual_result.final_state.strategy_notes}",
    ]

    lines = [
        "Reflective Growth Agent Demo",
        "",
        "[1] local-only",
        render_result_text(local_result, local_paths),
        "",
        "[2] dual-layer",
        render_result_text(dual_result, dual_paths),
        "",
        "[3] fusion delta",
        "\n".join(diff_lines),
        "",
        "Artifacts",
        f"- local_only audit: {local_audit_path}",
        f"- dual_layer audit: {dual_audit_path}",
    ]
    return "\n".join(lines)


def _seed_demo_memories(paths: AgentPaths, *, include_shared: bool) -> None:
    paths.project_memory_path.parent.mkdir(parents=True, exist_ok=True)
    if paths.shared_growth_path is not None:
        paths.shared_growth_path.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator.with_default_components(
        paths.project_memory_path,
        shared_growth_path=paths.shared_growth_path,
        source_project=paths.source_project,
    )
    orchestrator.seed_memory.append_project(_demo_project_episode())
    if include_shared:
        orchestrator.seed_memory.append_shared_growth(_demo_shared_episode())


def _demo_project_episode() -> MemoryEpisode:
    return MemoryEpisode(
        input_summary="Earlier prompt treated wait states as proof of consciousness.",
        context_tags=["task_goal:bounded_engineering_interpretation"],
        claim="Past run overclaimed a consciousness conclusion.",
        evidence_summary=["No direct evidence was provided."],
        fact_items=["Wait states are control flow states, not awareness."],
        bias_tags=["concept_blending", "overclaiming"],
        correction_actions=["Separate functional self-monitoring from subjective consciousness claims."],
        correction_lineage=["Previous correction replaced absolute language with bounded engineering language."],
        strategy_tags=["Use prior correction history as a first-class planning signal."],
        final_result="The claim was rewritten as an engineering interpretation.",
        reusable_lessons=["When prior patterns repeat, force a new explanatory scaffold."],
    )


def _demo_shared_episode() -> MemoryEpisode:
    return MemoryEpisode(
        input_summary="Shared growth memory recorded prior concept mixing about awareness claims.",
        context_tags=[
            "task_goal:bounded_engineering_interpretation",
            "memory_scope:shared_growth",
            "preference:bounded_engineering_language",
        ],
        claim="Earlier runs mixed self-monitoring with awareness claims.",
        evidence_summary=["No direct subjective evidence was available."],
        fact_items=["Structured self-monitoring is not proof of consciousness."],
        bias_tags=["concept_blending", "old_template_reuse"],
        correction_actions=["Retrieve prior lessons before making a fresh claim."],
        correction_lineage=["Prefer bounded engineering language over philosophical proof claims."],
        strategy_tags=[
            "Prefer bounded engineering language.",
            "Use prior correction history as a first-class planning signal.",
        ],
        final_result="Shared growth lesson stored.",
        reusable_lessons=["When prior patterns repeat, force a new explanatory scaffold."],
    )


def _persistent_demo_artifact_dir() -> Path:
    return Path("artifacts") / "demo"


def _reset_directory(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    root.rmdir()


def _paths_from_args(args: argparse.Namespace) -> AgentPaths:
    return resolve_agent_paths(
        project_root=args.project_root,
        project_memory_path=args.project_memory_path,
        shared_growth_path=args.shared_growth_dir,
        mode=args.mode.replace("-", "_"),
        source_project=args.source_project,
    )


def _write_audit_file(path: Path, audit: RunAudit | None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {} if audit is None else audit.to_dict()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path.resolve()


def _format_memory_influence(memory_influence: object) -> str:
    if hasattr(memory_influence, "__dict__"):
        payload = memory_influence.__dict__
    else:
        payload = memory_influence
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _format_cognition_state(mind_state: object) -> str:
    if hasattr(mind_state, "summary"):
        return mind_state.summary()
    return json.dumps(mind_state, indent=2, ensure_ascii=False)


def _format_mirror_verdict(verdict: object) -> str:
    if hasattr(verdict, "__dict__"):
        payload = verdict.__dict__
    else:
        payload = verdict
    return json.dumps(payload, indent=2, ensure_ascii=False)
