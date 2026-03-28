from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .commonsense_knowledge import CommonSenseKnowledgeLayer
from .cognition_agent import CognitionAgent
from .mirror_agent import MirrorAgent
from .models import CommonsenseAudit, KnowledgeAudit, MemoryEpisode, MemoryInfluence, MindState, MirrorVerdict, SelfState
from .scientific_knowledge import ScientificKnowledgeLayer
from .seed_memory import SeedMemory, SharedGrowthMemoryBackend


@dataclass
class CycleAudit:
    cycle: int
    cognition_state: MindState
    mirror_verdict: MirrorVerdict


@dataclass
class RunAudit:
    current_input: str
    task_goal: str
    memory_influence: MemoryInfluence
    knowledge_audit: KnowledgeAudit
    commonsense_audit: CommonsenseAudit
    cycles: list[CycleAudit]
    final_output: str
    final_state: MindState
    final_verdict: MirrorVerdict
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class OrchestratorResult:
    final_state: MindState
    final_verdict: MirrorVerdict
    output_text: str
    trace: list[str] = field(default_factory=list)
    audit: RunAudit | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "final_state": asdict(self.final_state),
            "final_verdict": asdict(self.final_verdict),
            "output_text": self.output_text,
            "trace": list(self.trace),
        }
        if self.audit is not None:
            payload["audit"] = self.audit.to_dict()
        return payload


class Orchestrator:
    """Runs a reflective loop and persists growth-oriented memory."""

    def __init__(
        self,
        cognition_agent: CognitionAgent,
        mirror_agent: MirrorAgent,
        seed_memory: SeedMemory,
        scientific_knowledge_layer: ScientificKnowledgeLayer,
        commonsense_knowledge_layer: CommonSenseKnowledgeLayer,
    ) -> None:
        self.cognition_agent = cognition_agent
        self.mirror_agent = mirror_agent
        self.seed_memory = seed_memory
        self.scientific_knowledge_layer = scientific_knowledge_layer
        self.commonsense_knowledge_layer = commonsense_knowledge_layer

    @classmethod
    def with_default_components(
        cls,
        storage_path: str | Path,
        shared_growth_path: str | Path | None = None,
        *,
        source_project: str = "reflective-growth-agent",
    ) -> "Orchestrator":
        shared_backend = (
            None
            if shared_growth_path is None
            else SharedGrowthMemoryBackend(shared_growth_path, source_project=source_project)
        )
        return cls(
            CognitionAgent(),
            MirrorAgent(),
            SeedMemory(storage_path, shared_growth_backend=shared_backend),
            ScientificKnowledgeLayer(),
            CommonSenseKnowledgeLayer(),
        )

    def run(self, current_input: str, task_goal: str, max_cycles: int = 4) -> OrchestratorResult:
        self_state = SelfState(active_goal=task_goal)
        trace: list[str] = []
        cycle_audits: list[CycleAudit] = []
        memory_influence = self.seed_memory.build_influence(current_input)
        knowledge_result = self.scientific_knowledge_layer.build_evidence(current_input, task_goal)
        commonsense_result = self.commonsense_knowledge_layer.build_evidence(current_input, task_goal)
        trace.append(
            "stage=memory "
            f"influence_matches={memory_influence.matched_episode_count} "
            f"project_matches={memory_influence.project_match_count} "
            f"shared_matches={memory_influence.shared_match_count}"
        )
        trace.extend(knowledge_result.trace)
        trace.extend(commonsense_result.trace)
        if memory_influence.has_signal():
            trace.append(
                "stage=memory "
                f"bias_alerts={memory_influence.bias_alerts} "
                f"correction_hints={memory_influence.correction_hints} "
                f"divergence_triggers={memory_influence.divergence_triggers}"
            )

        mind_state = self.cognition_agent.generate(
            current_input=current_input,
            task_goal=task_goal,
            self_state=self_state,
            memory_influence=memory_influence,
            evidence_pack=knowledge_result.evidence_pack,
            commonsense_evidence_pack=commonsense_result.evidence_pack,
        )

        for cycle in range(max_cycles):
            trace.append(f"cycle={cycle} stage=cognition claim={mind_state.main_claim!r}")
            verdict = self.mirror_agent.review(mind_state)
            cycle_audits.append(CycleAudit(cycle=cycle, cognition_state=mind_state, mirror_verdict=verdict))
            trace.append(f"cycle={cycle} stage=mirror verdict={verdict.verdict} issues={verdict.issues}")
            mind_state.self_state = mind_state.self_state.merge(verdict.self_state_update)

            if verdict.verdict == "pass":
                output_text = self._format_output(mind_state, verdict)
                self._write_memory(mind_state, verdict, output_text)
                return OrchestratorResult(
                    mind_state,
                    verdict,
                    output_text,
                    trace,
                    audit=RunAudit(
                        current_input=current_input,
                        task_goal=task_goal,
                        memory_influence=memory_influence,
                        knowledge_audit=knowledge_result.audit,
                        commonsense_audit=commonsense_result.audit,
                        cycles=cycle_audits,
                        final_output=output_text,
                        final_state=mind_state,
                        final_verdict=verdict,
                        trace=trace,
                    ),
                )

            if verdict.verdict == "retrieve":
                memory_influence = self.seed_memory.build_influence(current_input)
                trace.append(
                    f"cycle={cycle} stage=retrieve matched={memory_influence.matched_episode_count} "
                    f"project={memory_influence.project_match_count} "
                    f"shared={memory_influence.shared_match_count} "
                    f"lessons={memory_influence.correction_hints + memory_influence.strategy_hints}"
                )
                mind_state = self.cognition_agent.revise(mind_state, verdict.guidance, memory_influence)
                continue

            if verdict.verdict == "diverge":
                trace.append(
                    f"cycle={cycle} stage=diverge triggers={mind_state.memory_influence.divergence_triggers}"
                )
                mind_state = self.cognition_agent.revise(
                    mind_state,
                    verdict.guidance,
                    memory_influence=mind_state.memory_influence,
                    force_diverge=True,
                )
                continue

            if verdict.verdict == "wait":
                output_text = self._format_wait_output(mind_state, verdict)
                self._write_memory(mind_state, verdict, output_text)
                return OrchestratorResult(
                    mind_state,
                    verdict,
                    output_text,
                    trace,
                    audit=RunAudit(
                        current_input=current_input,
                        task_goal=task_goal,
                        memory_influence=memory_influence,
                        knowledge_audit=knowledge_result.audit,
                        commonsense_audit=commonsense_result.audit,
                        cycles=cycle_audits,
                        final_output=output_text,
                        final_state=mind_state,
                        final_verdict=verdict,
                        trace=trace,
                    ),
                )

            if verdict.verdict == "revise":
                mind_state = self.cognition_agent.revise(mind_state, verdict.guidance, memory_influence=mind_state.memory_influence)
                continue

        final_verdict = MirrorVerdict(
            verdict="wait",
            issues=["cycle_limit_reached"],
            guidance=["Stop and request more evidence or a narrower task."],
            self_state_update={"attention_mode": "paused"},
        )
        output_text = self._format_wait_output(mind_state, final_verdict)
        self._write_memory(mind_state, final_verdict, output_text)
        return OrchestratorResult(
            mind_state,
            final_verdict,
            output_text,
            trace,
            audit=RunAudit(
                current_input=current_input,
                task_goal=task_goal,
                memory_influence=memory_influence,
                knowledge_audit=knowledge_result.audit,
                commonsense_audit=commonsense_result.audit,
                cycles=cycle_audits,
                final_output=output_text,
                final_state=mind_state,
                final_verdict=final_verdict,
                trace=trace,
            ),
        )

    def _format_output(self, mind_state: MindState, verdict: MirrorVerdict) -> str:
        evidence_text = "; ".join(mind_state.evidence) if mind_state.evidence else "No direct evidence supplied."
        lessons_text = "; ".join(mind_state.retrieved_lessons) if mind_state.retrieved_lessons else "No prior lessons retrieved."
        knowledge_text = "none"
        if mind_state.evidence_pack is not None and mind_state.evidence_pack.records:
            knowledge_text = ", ".join(
                f"{record.entity}:{record.property}"
                for record in mind_state.evidence_pack.records
            )
        commonsense_text = "none"
        if mind_state.commonsense_evidence_pack is not None and mind_state.commonsense_evidence_pack.records:
            commonsense_text = ", ".join(
                f"{record.entity}:{record.relation}:{record.strength}"
                for record in mind_state.commonsense_evidence_pack.records
            )
        return (
            f"Result: {mind_state.main_claim}\n"
            f"Evidence summary: {evidence_text}\n"
            f"Knowledge evidence: {knowledge_text}\n"
            f"Commonsense evidence: {commonsense_text}\n"
            f"Memory influence: matches={mind_state.memory_influence.matched_episode_count}, lessons={lessons_text}\n"
            f"Mirror verdict: {verdict.verdict}\n"
            f"Uncertainty: {mind_state.self_state.uncertainty:.2f}"
        )

    def _format_wait_output(self, mind_state: MindState, verdict: MirrorVerdict) -> str:
        return (
            "Result deferred.\n"
            f"Reason: {', '.join(verdict.issues) or 'insufficient grounding'}\n"
            f"Needed next step: {' '.join(verdict.guidance)}\n"
            f"Memory pressure: {mind_state.self_state.memory_pressure:.2f}"
        )

    def _write_memory(self, mind_state: MindState, verdict: MirrorVerdict, output_text: str) -> None:
        project_episode = self._build_memory_episode(mind_state, verdict, output_text)
        self.seed_memory.append_project(project_episode)
        self.seed_memory.append_shared_growth(project_episode)

    def _build_memory_episode(
        self,
        mind_state: MindState,
        verdict: MirrorVerdict,
        output_text: str,
    ) -> MemoryEpisode:
        bias_tags = sorted(set(mind_state.self_risk + verdict.issues))
        return MemoryEpisode(
            input_summary=mind_state.current_input[:160],
            context_tags=self._derive_context_tags(mind_state),
            claim=mind_state.main_claim,
            evidence_summary=mind_state.evidence,
            fact_items=self._derive_fact_items(mind_state),
            bias_tags=bias_tags,
            correction_actions=verdict.guidance,
            correction_lineage=self._derive_correction_lineage(mind_state, verdict),
            strategy_tags=self._derive_strategy_tags(mind_state),
            final_result=output_text,
            reusable_lessons=self._derive_lessons(verdict),
        )

    def _derive_context_tags(self, mind_state: MindState) -> list[str]:
        tags = [
            "task_goal:" + mind_state.task_goal.replace(" ", "_"),
            "revision_count:" + str(mind_state.revision_count),
        ]
        tags.extend(mind_state.context_tags)
        return self._unique(tags)

    def _derive_fact_items(self, mind_state: MindState) -> list[str]:
        facts = [
            item.replace("Input mentions ", "")
            for item in mind_state.evidence
            if item
            and not item.startswith("Commonsense weak prior:")
            and not item.startswith("Commonsense blocked prior:")
        ]
        if mind_state.evidence_pack is not None:
            for record in mind_state.evidence_pack.records:
                value = record.normalized_value if record.normalized_value is not None else record.value
                unit = record.normalized_unit if record.normalized_unit is not None else record.unit
                facts.append(f"{record.entity} {record.property} = {value} {unit}".strip())
        if mind_state.commonsense_evidence_pack is not None:
            for record in mind_state.commonsense_evidence_pack.records:
                if record.strength in {"strong", "medium"}:
                    facts.append(f"{record.entity} {record.relation} = {record.value}")
        if "self-monitoring" in mind_state.main_claim.lower():
            facts.append("The output discusses functional self-monitoring rather than subjective certainty.")
        return self._unique(facts)

    def _derive_correction_lineage(self, mind_state: MindState, verdict: MirrorVerdict) -> list[str]:
        lineage = []
        if mind_state.revision_count > 0:
            lineage.append(f"Revision count reached {mind_state.revision_count}.")
        lineage.extend(verdict.guidance)
        return self._unique(lineage)

    def _derive_strategy_tags(self, mind_state: MindState) -> list[str]:
        tags = list(mind_state.strategy_notes)
        if mind_state.memory_influence.matched_episode_count > 0:
            tags.append("Use prior correction history as a first-class planning signal.")
        return self._unique(tags)

    def _derive_lessons(self, verdict: MirrorVerdict) -> list[str]:
        lessons = []
        if "overclaiming" in verdict.issues:
            lessons.append("Replace absolute claims with provisional wording.")
        if "concept_blending" in verdict.issues:
            lessons.append("Keep metacognitive control separate from consciousness language.")
        if "evidence_gap" in verdict.issues:
            lessons.append("State when evidence is missing before drawing conclusions.")
        if "weak_commonsense_as_fact" in verdict.issues:
            lessons.append("Keep weak commonsense priors advisory until structured sources confirm them.")
        if "structured_fact_priority_violation" in verdict.issues:
            lessons.append("Use structured geographic and entity fact sources before weak commonsense relations.")
        if "old_template_reuse" in verdict.issues or "needs_divergence" in verdict.issues:
            lessons.append("When prior patterns repeat, force a new explanatory scaffold.")
        if not lessons:
            lessons.append("Bound outputs with explicit uncertainty when evidence is limited.")
        return self._unique(lessons)

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
