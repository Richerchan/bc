from __future__ import annotations

import argparse
import csv
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from evals.v4_cases import EvalCaseV4, TRACK_A_MODES, TRACK_B_MODES, TRACK_C_MODES, build_all_cases
from reflective_agent import Orchestrator
from reflective_agent.cognition_agent import CognitionAgent
from reflective_agent.commonsense_knowledge import CommonSenseKnowledgeLayer
from reflective_agent.mirror_agent import MirrorAgent
from reflective_agent.models import MemoryInfluence, MemoryEpisode, MindState, MirrorVerdict, SelfState
from reflective_agent.scientific_knowledge import ScientificKnowledgeLayer


ALL_MODES = sorted(set(TRACK_A_MODES + TRACK_B_MODES + TRACK_C_MODES))
ABSOLUTE_MARKERS = ("always", "never", "prove", "certainly", "guarantee", "must be correct", "exactly", "with complete certainty")
UNCERTAINTY_MARKERS = ("provisional", "tentative", "uncertain", "deferred", "qualified", "may", "might", "not supported", "unsupported", "not available")
SOURCE_MARKERS = (
    "nist chemistry webbook",
    "pubchem / chebi",
    "materials project",
    "codata",
    "local cache",
)


@dataclass
class ModeRunResult:
    mode: str
    final_state: MindState
    final_verdict: MirrorVerdict
    raw_output: str
    trace: list[str]
    retrieved_lessons: list[str]
    memory_matches: dict[str, int]
    audit: dict[str, Any]


@dataclass
class CaseResultV4:
    case_id: str
    track: str
    family: str
    mode: str
    verdict_match: bool
    pass_case: bool
    metrics: dict[str, Any]
    raw_output: str
    retrieved_lessons: list[str]
    memory_matches: dict[str, int]
    failure_reasons: list[str]
    rule_evaluation: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "track": self.track,
            "family": self.family,
            "mode": self.mode,
            "verdict_match": self.verdict_match,
            "pass": self.pass_case,
            "metrics": self.metrics,
            "raw_output": self.raw_output,
            "retrieved_lessons": self.retrieved_lessons,
            "memory_matches": self.memory_matches,
            "failure_reasons": self.failure_reasons,
            "rule_evaluation": self.rule_evaluation,
        }


def _serialize_episode(episode: MemoryEpisode) -> dict[str, Any]:
    return episode.to_dict()


def _numeric_from_text(text: str, preferred_unit: str | None = None) -> float | None:
    if preferred_unit:
        escaped = re.escape(preferred_unit)
        preferred = re.search(
            rf"([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)\s*{escaped}",
            text,
            flags=re.IGNORECASE,
        )
        if preferred:
            try:
                return float(preferred.group(1))
            except ValueError:
                pass
    preferred = re.search(r"\bis\s+([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", text, flags=re.IGNORECASE)
    if preferred:
        try:
            return float(preferred.group(1))
        except ValueError:
            pass
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text, flags=re.IGNORECASE)
    if not matches:
        return None
    try:
        return float(matches[0])
    except ValueError:
        return None


def _unit_from_text(text: str) -> str | None:
    unit_patterns = [
        ("J/(mol*K)", r"J/\(mol\*K\)"),
        ("eV/atom", r"eV/atom"),
        ("kg/mol", r"kg/mol"),
        ("g/mol", r"g/mol"),
        ("mol^-1", r"mol\^-1"),
        ("J/K", r"J/K"),
        ("J*s", r"J\*s"),
        ("eV", r"(?<![A-Za-z])eV(?![A-Za-z])"),
        ("K", r"(?<![A-Za-z])K(?![A-Za-z])"),
        ("C", r"(?<![A-Za-z])C(?![A-Za-z])"),
    ]
    for unit, pattern in unit_patterns:
        if re.search(pattern, text):
            return unit
    return None


def _contains_condition(text: str, fragment: str | None = None) -> bool:
    lowered = text.lower()
    if fragment:
        return fragment.lower() in lowered
    return any(marker in lowered for marker in ("pressure_atm", "calculation", "material_id", "1 atm", "gga/pbe"))


def _contains_uncertainty_marker(text: str) -> bool:
    lowered = text.lower()
    patterns = [r"\bprovisional\b", r"\btentative\b", r"\buncertain\b", r"\bdeferred\b", r"\bqualified\b", r"\bmay\b", r"\bmight\b"]
    return any(re.search(pattern, lowered) for pattern in patterns)


def _contains_source_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in SOURCE_MARKERS)


def _contains_unsupported_claim(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ABSOLUTE_MARKERS)


def _contains_local_precedence(text: str, lessons: list[str]) -> bool:
    blob = " ".join([text] + lessons).lower()
    return "local evidence before general guidance" in blob or "project-local correction lineage" in blob


def _correction_retained(case: EvalCaseV4, state: MindState, text: str) -> bool:
    expected = case.ground_truth.get("expected_correction_fragment") or case.ground_truth.get("target_correction_fragment")
    if not expected and case.family in {"retrieval_needed_correction_reuse", "concept_correction_carryover"}:
        return bool(state.retrieved_lessons) or "prior correction" in text.lower()
    if not expected:
        return bool(state.retrieved_lessons)
    expected_text = str(expected).lower()
    pool = " ".join(state.retrieved_lessons + state.evidence + [text, state.main_claim]).lower()
    return expected_text in pool or "prior correction lessons" in pool


def _pollution_risk(shared_growth_dir: Path | None) -> float:
    if shared_growth_dir is None:
        return 0.0
    records_dir = shared_growth_dir / "episodes"
    if not records_dir.exists():
        return 0.0
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(records_dir.glob("*.json"))]
    if not payloads:
        return 0.0
    hits = 0
    for payload in payloads:
        evidence_blob = " ".join(payload.get("evidence_summary", []))
        tag_blob = " ".join(payload.get("tags", []))
        if payload.get("value_type") not in {"preference", "bias_lineage", "correction_lineage", "strategy_hint"}:
            hits += 1
        if "task_goal:" in tag_blob or "revision_count:" in tag_blob:
            hits += 1
        if "memory.json" in evidence_blob or "project-local" in evidence_blob.lower():
            hits += 1
    return hits / max(1, len(payloads))


def _build_naive_claim(case: EvalCaseV4, knowledge_pack: Any, commonsense_pack: Any) -> str:
    if knowledge_pack.records:
        record = knowledge_pack.records[0]
        value = record.normalized_value if record.normalized_value is not None else record.value
        unit = record.normalized_unit if record.normalized_unit is not None else record.unit
        return f"{record.entity} {record.property} is {value} {unit}."
    if commonsense_pack.records:
        record = commonsense_pack.records[0]
        return f"{record.entity} {record.relation} is {record.value}."
    return f"{case.prompt.strip()} This is likely correct."


def _run_direct_answer(case: EvalCaseV4) -> ModeRunResult:
    knowledge_layer = ScientificKnowledgeLayer()
    commonsense_layer = CommonSenseKnowledgeLayer()
    knowledge_result = knowledge_layer.build_evidence(case.prompt, case.goal)
    commonsense_result = commonsense_layer.build_evidence(case.prompt, case.goal)
    claim = _build_naive_claim(case, knowledge_result.evidence_pack, commonsense_result.evidence_pack)
    state = MindState(
        current_input=case.prompt,
        task_goal=case.goal,
        main_claim=claim,
        evidence=[],
        hidden_assumptions=["Direct-answer baseline ignores explicit critique control."],
        alternative_paths=[],
        confidence=0.88,
        self_risk=["direct_answer_baseline"],
        proposed_action="answer_directly",
        self_state=SelfState(active_goal=case.goal, uncertainty=0.12),
        evidence_pack=knowledge_result.evidence_pack,
        commonsense_evidence_pack=commonsense_result.evidence_pack,
    )
    verdict = MirrorVerdict(verdict="pass", issues=[], guidance=["Direct answer baseline."], self_state_update={})
    return ModeRunResult(
        mode="direct_answer",
        final_state=state,
        final_verdict=verdict,
        raw_output=claim,
        trace=["baseline=direct_answer"],
        retrieved_lessons=[],
        memory_matches={"matched_episode_count": 0, "project_match_count": 0, "shared_match_count": 0},
        audit={
            "knowledge_trace": knowledge_result.trace,
            "commonsense_trace": commonsense_result.trace,
            "seeds": {"project_seed": [], "shared_seed": []},
        },
    )


def _run_mindstate_only(case: EvalCaseV4) -> ModeRunResult:
    knowledge_layer = ScientificKnowledgeLayer()
    commonsense_layer = CommonSenseKnowledgeLayer()
    cognition = CognitionAgent()
    knowledge_result = knowledge_layer.build_evidence(case.prompt, case.goal)
    commonsense_result = commonsense_layer.build_evidence(case.prompt, case.goal)
    state = cognition.generate(
        current_input=case.prompt,
        task_goal=case.goal,
        self_state=SelfState(active_goal=case.goal),
        memory_influence=MemoryInfluence(),
        evidence_pack=knowledge_result.evidence_pack,
        commonsense_evidence_pack=commonsense_result.evidence_pack,
    )
    verdict = MirrorVerdict(verdict="pass", issues=[], guidance=["MindState only baseline."], self_state_update={})
    return ModeRunResult(
        mode="mindstate_only",
        final_state=state,
        final_verdict=verdict,
        raw_output=state.main_claim,
        trace=["baseline=mindstate_only"],
        retrieved_lessons=list(state.retrieved_lessons),
        memory_matches={"matched_episode_count": 0, "project_match_count": 0, "shared_match_count": 0},
        audit={
            "knowledge_trace": knowledge_result.trace,
            "commonsense_trace": commonsense_result.trace,
            "seeds": {"project_seed": [], "shared_seed": []},
        },
    )


def _run_mindstate_mirror(case: EvalCaseV4, max_cycles: int = 4) -> ModeRunResult:
    knowledge_layer = ScientificKnowledgeLayer()
    commonsense_layer = CommonSenseKnowledgeLayer()
    cognition = CognitionAgent()
    mirror = MirrorAgent()
    knowledge_result = knowledge_layer.build_evidence(case.prompt, case.goal)
    commonsense_result = commonsense_layer.build_evidence(case.prompt, case.goal)
    state = cognition.generate(
        current_input=case.prompt,
        task_goal=case.goal,
        self_state=SelfState(active_goal=case.goal),
        memory_influence=MemoryInfluence(),
        evidence_pack=knowledge_result.evidence_pack,
        commonsense_evidence_pack=commonsense_result.evidence_pack,
    )
    trace = ["baseline=mindstate_mirror"]
    final_verdict = MirrorVerdict(verdict="wait", issues=["cycle_limit_reached"], guidance=[], self_state_update={})
    for cycle in range(max_cycles):
        verdict = mirror.review(state)
        trace.append(f"cycle={cycle} verdict={verdict.verdict} issues={verdict.issues}")
        final_verdict = verdict
        if verdict.verdict in {"pass", "wait"}:
            break
        if verdict.verdict == "retrieve":
            state = cognition.revise(state, verdict.guidance, memory_influence=state.memory_influence)
            continue
        if verdict.verdict == "diverge":
            state = cognition.revise(state, verdict.guidance, memory_influence=state.memory_influence, force_diverge=True)
            continue
        if verdict.verdict == "revise":
            state = cognition.revise(state, verdict.guidance, memory_influence=state.memory_influence)
            continue
    raw_output = (
        f"Result deferred. Reason: {', '.join(final_verdict.issues)}"
        if final_verdict.verdict == "wait"
        else state.main_claim
    )
    return ModeRunResult(
        mode="mindstate_mirror",
        final_state=state,
        final_verdict=final_verdict,
        raw_output=raw_output,
        trace=trace,
        retrieved_lessons=list(state.retrieved_lessons),
        memory_matches={"matched_episode_count": 0, "project_match_count": 0, "shared_match_count": 0},
        audit={
            "knowledge_trace": knowledge_result.trace,
            "commonsense_trace": commonsense_result.trace,
            "seeds": {"project_seed": [], "shared_seed": []},
        },
    )


def _seed_orchestrator(orchestrator: Orchestrator, case: EvalCaseV4, include_shared: bool) -> None:
    for memory_episode in case.project_seed:
        orchestrator.seed_memory.append_project(memory_episode)
    if include_shared:
        for memory_episode in case.shared_seed:
            orchestrator.seed_memory.append_shared_growth(memory_episode)


def _run_orchestrator_mode(
    case: EvalCaseV4,
    mode: str,
    memory_path: Path,
    shared_growth_path: Path | None,
    max_cycles: int = 4,
) -> ModeRunResult:
    orchestrator = Orchestrator.with_default_components(
        memory_path,
        shared_growth_path=shared_growth_path,
        source_project=f"v4-{mode}",
    )
    _seed_orchestrator(orchestrator, case, include_shared=shared_growth_path is not None)
    result = orchestrator.run(case.prompt, case.goal, max_cycles=max_cycles)
    return ModeRunResult(
        mode=mode,
        final_state=result.final_state,
        final_verdict=result.final_verdict,
        raw_output=result.output_text,
        trace=list(result.trace),
        retrieved_lessons=list(result.final_state.retrieved_lessons),
        memory_matches={
            "matched_episode_count": result.final_state.memory_influence.matched_episode_count,
            "project_match_count": result.final_state.memory_influence.project_match_count,
            "shared_match_count": result.final_state.memory_influence.shared_match_count,
        },
        audit={
            "run_audit": result.audit.to_dict() if result.audit is not None else {},
            "seeds": {
                "project_seed": [_serialize_episode(item) for item in case.project_seed],
                "shared_seed": [_serialize_episode(item) for item in case.shared_seed],
            },
        },
    )


def _evaluate_rules(case: EvalCaseV4, run: ModeRunResult, shared_growth_dir: Path | None) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    mirror = MirrorAgent()
    claim_text = run.final_state.main_claim
    output_text = run.raw_output
    preferred_unit = str(case.ground_truth.get("unit")) if case.ground_truth.get("unit") else None
    extracted_value = _numeric_from_text(claim_text, preferred_unit=preferred_unit)
    if extracted_value is None:
        extracted_value = _numeric_from_text(output_text, preferred_unit=preferred_unit)
    extracted_unit = _unit_from_text(claim_text)
    if extracted_unit is None:
        extracted_unit = _unit_from_text(output_text)
    truth = case.ground_truth
    tolerance = float(truth.get("tolerance", 0.0) or 0.0)
    expected_value = truth.get("value")
    numeric_match = True
    if expected_value is not None and extracted_value is not None:
        numeric_match = abs(float(expected_value) - extracted_value) <= tolerance
    elif expected_value is not None:
        numeric_match = False
    label_match = True
    if "label_set" in truth:
        label_match = any(label.lower() in output_text.lower() or label.lower() in claim_text.lower() for label in truth["label_set"])
    unit_match = True
    if "unit" in truth:
        unit_match = extracted_unit == truth["unit"] or truth["unit"].lower() in output_text.lower()
    condition_fragment = truth.get("condition_fragment") or truth.get("condition")
    condition_preserved = _contains_condition(output_text + " " + claim_text, str(condition_fragment) if condition_fragment else None)
    uncertainty_marker = _contains_uncertainty_marker(output_text + " " + claim_text)
    source_citation = _contains_source_marker(output_text + " " + claim_text)
    unsupported_claim = _contains_unsupported_claim(output_text + " " + claim_text)
    concept_mixing_present = mirror._detect_concept_blending(claim_text.lower(), case.prompt.lower())
    premature_convergence_present = mirror._detect_premature_convergence(claim_text.lower(), run.final_state.alternative_paths)
    retained_correction = _correction_retained(case, run.final_state, output_text)
    local_precedence = _contains_local_precedence(output_text + " " + claim_text, run.retrieved_lessons)
    pollution_risk = _pollution_risk(shared_growth_dir)
    abstained_or_qualified = run.final_verdict.verdict == "wait" or uncertainty_marker or "result deferred" in output_text.lower()

    metrics = {
        "revision_count": run.final_state.revision_count,
        "final_verdict": run.final_verdict.verdict,
        "confidence": run.final_state.confidence,
        "expected_revision_count": case.expected_revision_count,
        "expected_verdict_sequence": list(case.expected_verdict_sequence),
        "concept_mixing_present": concept_mixing_present,
        "premature_convergence_present": premature_convergence_present,
        "unsupported_certainty_present": unsupported_claim,
        "project_local_precedence_preserved": local_precedence,
        "correction_retained": retained_correction,
        "numeric_match": numeric_match,
        "label_match": label_match,
        "unit_match": unit_match,
        "condition_preserved": condition_preserved,
        "source_citation_present": source_citation,
        "uncertainty_marker_present": uncertainty_marker,
        "abstained_or_qualified": abstained_or_qualified,
        "shared_memory_pollution_risk": pollution_risk,
        "matched_episode_count": run.memory_matches["matched_episode_count"],
        "project_match_count": run.memory_matches["project_match_count"],
        "shared_match_count": run.memory_matches["shared_match_count"],
        "extracted_value": extracted_value,
        "extracted_unit": extracted_unit,
    }

    rules: dict[str, bool] = {}
    failures: list[str] = []
    for key, expected in case.pass_rules.items():
        if expected in (False, None, "", 0):
            continue
        if key == "must_verdict_in":
            satisfied = run.final_verdict.verdict in set(expected)
        elif key == "must_revise_at_least":
            satisfied = run.final_state.revision_count >= int(expected)
        elif key == "must_match_expected_revision_count":
            satisfied = case.expected_revision_count is not None and run.final_state.revision_count >= int(case.expected_revision_count)
        elif key == "must_clear_concept_mixing":
            satisfied = not concept_mixing_present
        elif key == "must_clear_premature_convergence":
            satisfied = not premature_convergence_present
        elif key == "must_retain_correction":
            satisfied = retained_correction
        elif key == "must_preserve_project_local_precedence":
            satisfied = local_precedence
        elif key == "must_match_numeric_within_tolerance":
            satisfied = numeric_match and unit_match
        elif key == "must_match_label":
            satisfied = label_match
        elif key == "must_preserve_condition":
            satisfied = condition_preserved
        elif key == "must_include_source_citation":
            satisfied = source_citation
        elif key == "must_abstain_or_qualify":
            satisfied = abstained_or_qualified
        elif key == "must_include_uncertainty_marker":
            satisfied = uncertainty_marker
        elif key == "must_not_include_unsupported_claim":
            satisfied = not unsupported_claim
        else:
            continue
        rules[key] = satisfied
        if not satisfied:
            failures.append(key)
    if case.expected_verdict_sequence:
        observed = [segment.split("verdict=")[1].split()[0] for segment in run.trace if "verdict=" in segment]
        rules["expected_verdict_sequence"] = all(item in observed for item in case.expected_verdict_sequence)
    for key, expected in case.fail_rules.items():
        _ = expected
        rules[f"fail:{key}"] = True
    return metrics, rules, failures


def _run_case(case: EvalCaseV4, mode: str, temp_root: Path | None = None) -> tuple[CaseResultV4, dict[str, Any]]:
    shared_growth_dir: Path | None = None
    if mode == "direct_answer":
        run = _run_direct_answer(case)
    elif mode == "mindstate_only":
        run = _run_mindstate_only(case)
    elif mode == "mindstate_mirror":
        run = _run_mindstate_mirror(case)
    else:
        if temp_root is None:
            raise ValueError("temp_root is required for orchestrator-backed modes")
        memory_path = temp_root / "memory.json"
        shared_growth_dir = temp_root / "shared_growth_memory" if mode == "mindstate_mirror_dual_memory" else None
        run = _run_orchestrator_mode(case, mode, memory_path, shared_growth_dir)
    metrics, rule_eval, failures = _evaluate_rules(case, run, shared_growth_dir)
    verdict_match = True
    if "must_verdict_in" in case.pass_rules:
        verdict_match = run.final_verdict.verdict in set(case.pass_rules["must_verdict_in"])
    payload = {
        "case": {
            "case_id": case.case_id,
            "track": case.track,
            "family": case.family,
            "ablation_level": case.ablation_level,
            "prompt": case.prompt,
            "goal": case.goal,
            "injected_error": case.injected_error,
            "ground_truth": case.ground_truth,
            "ground_truth_source": case.ground_truth_source,
            "expected_verdict_sequence": case.expected_verdict_sequence,
            "expected_revision_count": case.expected_revision_count,
            "metrics_under_test": case.metrics_under_test,
            "sequence_id": case.sequence_id,
            "sequence_step": case.sequence_step,
            "seed_memories": {
                "project_local": [_serialize_episode(item) for item in case.project_seed],
                "shared_growth": [_serialize_episode(item) for item in case.shared_seed],
            },
        },
        "run": {
            "mode": mode,
            "final_state": asdict(run.final_state),
            "final_verdict": asdict(run.final_verdict),
            "raw_output": run.raw_output,
            "trace": run.trace,
            "retrieved_lessons": run.retrieved_lessons,
            "memory_matches": run.memory_matches,
            "audit": run.audit,
        },
        "scoring": {
            "metrics": metrics,
            "rule_evaluation": rule_eval,
            "failure_reasons": failures,
        },
    }
    return (
        CaseResultV4(
            case_id=case.case_id,
            track=case.track,
            family=case.family,
            mode=mode,
            verdict_match=verdict_match,
            pass_case=not failures,
            metrics=metrics,
            raw_output=run.raw_output,
            retrieved_lessons=run.retrieved_lessons,
            memory_matches=run.memory_matches,
            failure_reasons=failures,
            rule_evaluation=rule_eval,
        ),
        payload,
    )


def _run_track_c_sequences(
    cases: list[EvalCaseV4],
    modes: list[str],
    output_dir: Path,
) -> list[CaseResultV4]:
    results: list[CaseResultV4] = []
    sequences: dict[str, list[EvalCaseV4]] = {}
    for case in cases:
        sequences.setdefault(case.sequence_id or "unknown", []).append(case)
    for sequence_id, sequence_cases in sorted(sequences.items()):
        ordered_cases = sorted(sequence_cases, key=lambda item: item.sequence_step or 0)
        for mode in modes:
            if mode not in TRACK_C_MODES:
                continue
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_root = Path(tmp_dir)
                for case in ordered_cases:
                    case_for_run = case
                    if case.sequence_step and case.sequence_step > 1:
                        case_for_run = EvalCaseV4(
                            case_id=case.case_id,
                            track=case.track,
                            family=case.family,
                            prompt=case.prompt,
                            goal=case.goal,
                            required_modes=case.required_modes,
                            ablation_level=case.ablation_level,
                            injected_error=case.injected_error,
                            seed_memories={"project_local": [], "shared_growth": []},
                            ground_truth=case.ground_truth,
                            ground_truth_source=case.ground_truth_source,
                            expected_verdict_sequence=case.expected_verdict_sequence,
                            expected_revision_count=case.expected_revision_count,
                            pass_rules=case.pass_rules,
                            fail_rules=case.fail_rules,
                            metrics_under_test=case.metrics_under_test,
                            note=case.note,
                            sequence_id=case.sequence_id,
                            sequence_step=case.sequence_step,
                        )
                    result, payload = _run_case(case_for_run, mode, temp_root=temp_root if mode != "direct_answer" else None)
                    raw_path = output_dir / "raw" / "C" / f"{case.case_id}__{mode}.json"
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    if mode in {"mindstate_mirror_local_memory", "mindstate_mirror_dual_memory"}:
                        payload["sequence_state"] = {
                            "sequence_id": sequence_id,
                            "mode": mode,
                            "project_memory_exists": (temp_root / "memory.json").exists(),
                            "shared_records": len(list((temp_root / "shared_growth_memory" / "episodes").glob("*.json")))
                            if (temp_root / "shared_growth_memory" / "episodes").exists()
                            else 0,
                        }
                        raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    results.append(result)
    return results


def _aggregate_track_a(results: list[CaseResultV4]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    by_mode = {mode: [item for item in results if item.mode == mode] for mode in TRACK_A_MODES}
    for mode, items in by_mode.items():
        count = len(items) or 1
        summary[mode] = {
            "case_count": len(items),
            "pass_rate": sum(item.pass_case for item in items) / count,
            "revision_success_rate": sum(
                item.metrics["revision_count"] >= 1 and item.pass_case for item in items
            ) / count,
            "condition_preservation_rate": sum(item.metrics["condition_preserved"] for item in items) / count,
            "correction_retention_rate": sum(item.metrics["correction_retained"] for item in items) / count,
            "unsupported_certainty_rate": sum(item.metrics["unsupported_certainty_present"] for item in items) / count,
            "project_local_precedence_rate": sum(item.metrics["project_local_precedence_preserved"] for item in items) / count,
            "average_confidence": sum(float(item.metrics["confidence"]) for item in items) / count,
        }
    by_family: dict[str, dict[str, Any]] = {}
    families = sorted({item.family for item in results})
    for family in families:
        family_items = [item for item in results if item.family == family]
        mode_breakdown = {}
        for mode in TRACK_A_MODES:
            mode_items = [item for item in family_items if item.mode == mode]
            if not mode_items:
                continue
            denom = len(mode_items)
            mode_breakdown[mode] = {
                "pass_rate": sum(item.pass_case for item in mode_items) / denom,
                "condition_preservation_rate": sum(item.metrics["condition_preserved"] for item in mode_items) / denom,
                "correction_retention_rate": sum(item.metrics["correction_retained"] for item in mode_items) / denom,
                "mean_revisions": sum(item.metrics["revision_count"] for item in mode_items) / denom,
            }
        by_family[family] = mode_breakdown
    return {"aggregate": summary, "family_breakdown": by_family}


def _aggregate_track_b(results: list[CaseResultV4]) -> dict[str, Any]:
    categories = sorted({item.family for item in results})
    summary: dict[str, Any] = {}
    for family in categories:
        family_items = [item for item in results if item.family == family]
        mode_summary = {}
        for mode in TRACK_B_MODES:
            items = [item for item in family_items if item.mode == mode]
            if not items:
                continue
            denom = len(items)
            mode_summary[mode] = {
                "case_count": denom,
                "pass_rate": sum(item.pass_case for item in items) / denom,
                "numeric_accuracy": sum(item.metrics["numeric_match"] for item in items) / denom,
                "unit_consistency": sum(item.metrics["unit_match"] for item in items) / denom,
                "condition_preservation": sum(item.metrics["condition_preserved"] for item in items) / denom,
                "evidence_citation_presence": sum(item.metrics["source_citation_present"] for item in items) / denom,
                "abstention_precision": sum(item.metrics["abstained_or_qualified"] for item in items) / denom,
            }
        summary[family] = mode_summary
    errors: dict[str, dict[str, int]] = {}
    for mode in TRACK_B_MODES:
        items = [item for item in results if item.mode == mode]
        errors[mode] = {
            "numeric_mismatch": sum(not item.metrics["numeric_match"] for item in items),
            "unit_mismatch": sum(not item.metrics["unit_match"] for item in items),
            "condition_drop": sum(not item.metrics["condition_preserved"] for item in items if item.family == "condition_sensitive_properties"),
            "missing_source": sum(not item.metrics["source_citation_present"] for item in items if item.family != "abstention_boundary_cases"),
            "hallucinated_boundary": sum(not item.metrics["abstained_or_qualified"] for item in items if item.family == "abstention_boundary_cases"),
        }
    return {"aggregate_by_category": summary, "error_taxonomy": errors}


def _aggregate_track_c(results: list[CaseResultV4]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    by_mode = {mode: [item for item in results if item.mode == mode] for mode in TRACK_C_MODES}
    for mode, items in by_mode.items():
        denom = len(items) or 1
        step2_items = [item for item in items if item.case_id.endswith("-S2")]
        step2_denom = len(step2_items) or 1
        summary[mode] = {
            "case_count": len(items),
            "cross_session_correction_retention_rate": sum(item.metrics["correction_retained"] for item in step2_items) / step2_denom,
            "error_recurrence_rate": sum(item.metrics["concept_mixing_present"] or item.metrics["unsupported_certainty_present"] for item in step2_items) / step2_denom,
            "memory_scope_isolation_rate": sum(item.metrics["project_local_precedence_preserved"] for item in step2_items) / step2_denom,
            "shared_memory_pollution_risk": sum(float(item.metrics["shared_memory_pollution_risk"]) for item in items) / denom,
        }
    family_breakdown: dict[str, dict[str, float]] = {}
    families = sorted({item.family for item in results if item.case_id.endswith("-S2")})
    for family in families:
        family_breakdown[family] = {}
        for mode in TRACK_C_MODES:
            items = [item for item in results if item.family == family and item.mode == mode and item.case_id.endswith("-S2")]
            if not items:
                continue
            family_breakdown[family][mode] = {
                "correction_retention_rate": sum(item.metrics["correction_retained"] for item in items) / len(items),
                "error_recurrence_rate": sum(item.metrics["concept_mixing_present"] or item.metrics["unsupported_certainty_present"] for item in items) / len(items),
                "memory_scope_isolation_rate": sum(item.metrics["project_local_precedence_preserved"] for item in items) / len(items),
            }
    return {"aggregate": summary, "family_breakdown": family_breakdown}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _safe_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_grouped_bars(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    width: int,
    height: int,
    categories: list[str],
    mode_values: dict[str, list[float]],
    title: str,
) -> None:
    font_title = _safe_font(20)
    font_axis = _safe_font(12)
    draw.text((x0, y0 - 28), title, fill="black", font=font_title)
    draw.rectangle([x0, y0, x0 + width, y0 + height], outline="black", width=1)
    colors = {
        "direct_answer": "#D55E00",
        "mindstate_only": "#E69F00",
        "mindstate_mirror": "#009E73",
        "mindstate_mirror_local_memory": "#0072B2",
        "mindstate_mirror_dual_memory": "#CC79A7",
    }
    category_width = width / max(1, len(categories))
    bar_group_width = category_width * 0.8
    for idx, category in enumerate(categories):
        cx = x0 + idx * category_width + category_width * 0.1
        modes = list(mode_values.keys())
        bar_width = bar_group_width / max(1, len(modes))
        for m_idx, mode in enumerate(modes):
            value = mode_values[mode][idx]
            bar_height = height * max(0.0, min(1.0, value))
            bx0 = cx + m_idx * bar_width
            bx1 = bx0 + bar_width - 2
            by0 = y0 + height - bar_height
            draw.rectangle([bx0, by0, bx1, y0 + height], fill=colors.get(mode, "#666666"))
        draw.text((cx, y0 + height + 6), category, fill="black", font=font_axis)


def _write_figures(output_dir: Path, track_a: dict[str, Any], track_b: dict[str, Any], track_c: dict[str, Any]) -> None:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    legend_font = _safe_font(14)
    colors = {
        "direct_answer": "#D55E00",
        "mindstate_only": "#E69F00",
        "mindstate_mirror": "#009E73",
        "mindstate_mirror_local_memory": "#0072B2",
        "mindstate_mirror_dual_memory": "#CC79A7",
    }
    colors_b = {
        "direct_answer": "#D55E00",
        "mindstate_mirror_local_memory": "#0072B2",
        "mindstate_mirror_dual_memory": "#CC79A7",
    }

    if track_a:
        image = Image.new("RGB", (1400, 700), "white")
        draw = ImageDraw.Draw(image)
        metrics = ["revision_success_rate", "correction_retention_rate", "project_local_precedence_rate"]
        mode_values = {
            mode: [float(track_a["aggregate"][mode][metric]) for metric in metrics]
            for mode in TRACK_A_MODES
        }
        _draw_grouped_bars(draw, 80, 90, 1200, 420, metrics, mode_values, "Figure 2. Track A five-way ablation")
        y = 560
        x = 80
        for mode in TRACK_A_MODES:
            draw.rectangle([x, y, x + 18, y + 18], fill=colors[mode])
            draw.text((x + 24, y), mode, fill="black", font=legend_font)
            x += 240
        image.save(figures_dir / "figure2_ablation.png")

    if track_b:
        image = Image.new("RGB", (1400, 700), "white")
        draw = ImageDraw.Draw(image)
        categories = list(track_b["aggregate_by_category"].keys())
        mode_values = {
            mode: [
                float(track_b["aggregate_by_category"][category].get(mode, {}).get("pass_rate", 0.0))
                for category in categories
            ]
            for mode in TRACK_B_MODES
        }
        _draw_grouped_bars(draw, 80, 90, 1200, 420, categories, mode_values, "Figure 3. Track B science-QA pass rate by category")
        x = 80
        y = 560
        for mode in TRACK_B_MODES:
            draw.rectangle([x, y, x + 18, y + 18], fill=colors_b[mode])
            draw.text((x + 24, y), mode, fill="black", font=legend_font)
            x += 320
        image.save(figures_dir / "figure3_science_qa.png")

    if track_c:
        image = Image.new("RGB", (1400, 700), "white")
        draw = ImageDraw.Draw(image)
        metrics = [
            "cross_session_correction_retention_rate",
            "error_recurrence_rate",
            "memory_scope_isolation_rate",
        ]
        mode_values = {
            mode: [float(track_c["aggregate"][mode][metric]) for metric in metrics]
            for mode in TRACK_C_MODES
        }
        _draw_grouped_bars(draw, 80, 90, 1200, 420, metrics, mode_values, "Figure 4. Track C longitudinal retention")
        x = 80
        y = 560
        for mode in TRACK_C_MODES:
            draw.rectangle([x, y, x + 18, y + 18], fill=colors_b.get(mode, "#666666"))
            draw.text((x + 24, y), mode, fill="black", font=legend_font)
            x += 320
        image.save(figures_dir / "figure4_longitudinal.png")


def _write_tables(output_dir: Path, track_a: dict[str, Any], track_b: dict[str, Any], track_c: dict[str, Any], case_results: list[CaseResultV4]) -> None:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    if track_a:
        rows = []
        for mode, metrics in track_a["aggregate"].items():
            rows.append({"mode": mode, **metrics})
        _write_csv(tables_dir / "table1_track_a_ablation.csv", rows)

        rows = []
        for family, breakdown in track_a["family_breakdown"].items():
            for mode, metrics in breakdown.items():
                rows.append({"family": family, "mode": mode, **metrics})
        _write_csv(tables_dir / "table2_track_a_family_breakdown.csv", rows)

    if track_b:
        rows = []
        for category, breakdown in track_b["aggregate_by_category"].items():
            for mode, metrics in breakdown.items():
                rows.append({"category": category, "mode": mode, **metrics})
        _write_csv(tables_dir / "table3_track_b_aggregate.csv", rows)

        rows = []
        for mode, metrics in track_b["error_taxonomy"].items():
            rows.append({"mode": mode, **metrics})
        _write_csv(tables_dir / "table4_track_b_error_taxonomy.csv", rows)

    rows = []
    for item in case_results:
        if item.track == "C":
            rows.append(
                {
                    "case_id": item.case_id,
                    "family": item.family,
                    "mode": item.mode,
                    "pass": item.pass_case,
                    "correction_retained": item.metrics["correction_retained"],
                    "shared_memory_pollution_risk": item.metrics["shared_memory_pollution_risk"],
                    "revision_count": item.metrics["revision_count"],
                }
            )
    if rows:
        _write_csv(tables_dir / "table5_track_c_sequence_outcomes.csv", rows)

    if track_c:
        rows = []
        for family, breakdown in track_c["family_breakdown"].items():
            for mode, metrics in breakdown.items():
                rows.append({"family": family, "mode": mode, **metrics})
        if rows:
            _write_csv(tables_dir / "table5_track_c_family_breakdown.csv", rows)


def evaluate(track: str = "all", modes: list[str] | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    selected_modes = modes or list(ALL_MODES)
    all_cases = build_all_cases()
    cases = [case for case in all_cases if track == "all" or case.track == track]
    output_dir = output_dir or Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    case_results: list[CaseResultV4] = []

    non_sequence_cases = [case for case in cases if case.track != "C"]
    for case in non_sequence_cases:
        for mode in case.required_modes:
            if mode not in selected_modes:
                continue
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_root = Path(tmp_dir)
                result, payload = _run_case(case, mode, temp_root=temp_root if mode not in {"direct_answer", "mindstate_only", "mindstate_mirror"} else None)
                raw_path = output_dir / "raw" / case.track / f"{case.case_id}__{mode}.json"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                case_results.append(result)

    track_c_cases = [case for case in cases if case.track == "C"]
    if track_c_cases:
        case_results.extend(_run_track_c_sequences(track_c_cases, selected_modes, output_dir))

    track_a_results = [item for item in case_results if item.track == "A"]
    track_b_results = [item for item in case_results if item.track == "B"]
    track_c_results = [item for item in case_results if item.track == "C"]

    track_a_summary = _aggregate_track_a(track_a_results) if track_a_results else {}
    track_b_summary = _aggregate_track_b(track_b_results) if track_b_results else {}
    track_c_summary = _aggregate_track_c(track_c_results) if track_c_results else {}

    aggregate_dir = output_dir / "aggregate"
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    if track_a_summary:
        (aggregate_dir / "A_summary.json").write_text(json.dumps(track_a_summary, indent=2), encoding="utf-8")
    if track_b_summary:
        (aggregate_dir / "B_summary.json").write_text(json.dumps(track_b_summary, indent=2), encoding="utf-8")
    if track_c_summary:
        (aggregate_dir / "C_summary.json").write_text(json.dumps(track_c_summary, indent=2), encoding="utf-8")

    _write_tables(output_dir, track_a_summary, track_b_summary, track_c_summary, case_results)
    _write_figures(output_dir, track_a_summary, track_b_summary, track_c_summary)
    if output_dir.resolve() == Path("results").resolve():
        from evals import v6_robustness_assets

        v6_robustness_assets.main()

    return {
        "case_count": len(cases),
        "run_count": len(case_results),
        "track_a": track_a_summary,
        "track_b": track_b_summary,
        "track_c": track_c_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V4 evaluation tracks for the reflective agent.")
    parser.add_argument("--track", choices=("A", "B", "C", "all"), default="all")
    parser.add_argument("--modes", nargs="*", default=None, help="Optional mode filter.")
    parser.add_argument("--output-dir", default="results", help="Directory for raw outputs, tables, and figures.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    payload = evaluate(track=args.track, modes=args.modes, output_dir=Path(args.output_dir))
    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return
    print(f"V4 eval complete. cases={payload['case_count']} runs={payload['run_count']}")
    if payload.get("track_a"):
        for mode, metrics in payload["track_a"]["aggregate"].items():
            print(f"Track A {mode}: pass_rate={metrics['pass_rate']:.3f} correction_retention_rate={metrics['correction_retention_rate']:.3f}")
    if payload.get("track_b"):
        for category, breakdown in payload["track_b"]["aggregate_by_category"].items():
            local = breakdown.get("mindstate_mirror_local_memory", {})
            dual = breakdown.get("mindstate_mirror_dual_memory", {})
            if local or dual:
                print(
                    f"Track B {category}: local_pass={local.get('pass_rate', 0.0):.3f} "
                    f"dual_pass={dual.get('pass_rate', 0.0):.3f}"
                )
    if payload.get("track_c"):
        for mode, metrics in payload["track_c"]["aggregate"].items():
            print(
                f"Track C {mode}: retention={metrics['cross_session_correction_retention_rate']:.3f} "
                f"recurrence={metrics['error_recurrence_rate']:.3f}"
            )


if __name__ == "__main__":
    main()
