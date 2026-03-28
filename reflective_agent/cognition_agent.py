from __future__ import annotations

from dataclasses import replace

from .models import CommonsenseEvidencePack, EvidencePack, MemoryInfluence, MindState, SelfState


class CognitionAgent:
    """Builds and revises structured cognitive states."""

    def generate(
        self,
        current_input: str,
        task_goal: str,
        self_state: SelfState | None = None,
        memory_influence: MemoryInfluence | None = None,
        evidence_pack: EvidencePack | None = None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None = None,
        revision_count: int = 0,
        force_diverge: bool = False,
    ) -> MindState:
        memory_influence = memory_influence or MemoryInfluence()
        self_state = self_state or SelfState(active_goal=task_goal)
        lowered = current_input.lower()
        evidence = self._extract_evidence(current_input, memory_influence, evidence_pack, commonsense_evidence_pack)
        assumptions = self._extract_assumptions(lowered, memory_influence, evidence_pack, commonsense_evidence_pack)
        alternatives = self._alternative_paths(lowered, memory_influence, evidence_pack, commonsense_evidence_pack)
        claim = self._build_claim(current_input, memory_influence, evidence_pack, commonsense_evidence_pack, force_diverge)
        confidence = self._estimate_confidence(evidence, lowered, memory_influence, evidence_pack, commonsense_evidence_pack)
        risks = self._build_risks(evidence, lowered, memory_influence, evidence_pack, commonsense_evidence_pack)
        action = self._build_action(memory_influence, force_diverge)
        context_tags = self._build_context_tags(current_input, task_goal, memory_influence, evidence_pack, commonsense_evidence_pack)
        strategy_notes = self._build_strategy_notes(memory_influence, force_diverge)

        continuity = list(self_state.continuity_notes)
        continuity.append(f"Revision #{revision_count}: built candidate cognition state.")
        if memory_influence.has_signal():
            continuity.append(
                f"Memory influence engaged from {memory_influence.matched_episode_count} prior episode(s)."
            )

        updated_state = replace(
            self_state,
            active_goal=task_goal,
            memory_pressure=min(1.0, 0.15 * memory_influence.matched_episode_count),
            continuity_notes=continuity,
        )

        return MindState(
            current_input=current_input,
            task_goal=task_goal,
            main_claim=claim,
            evidence=evidence,
            hidden_assumptions=assumptions,
            alternative_paths=alternatives,
            confidence=confidence,
            self_risk=risks,
            proposed_action=action,
            self_state=updated_state,
            context_tags=context_tags,
            strategy_notes=strategy_notes,
            memory_influence=memory_influence,
            evidence_pack=evidence_pack,
            commonsense_evidence_pack=commonsense_evidence_pack,
            revision_count=revision_count,
            retrieved_lessons=memory_influence.correction_hints + memory_influence.strategy_hints,
        )

    def revise(
        self,
        mind_state: MindState,
        guidance: list[str],
        memory_influence: MemoryInfluence | None = None,
        force_diverge: bool = False,
    ) -> MindState:
        memory_influence = memory_influence or mind_state.memory_influence
        revised_claim = self._rewrite_claim(
            claim=mind_state.main_claim,
            guidance=guidance,
            memory_influence=memory_influence,
            force_diverge=force_diverge,
        )

        revised_evidence = list(mind_state.evidence)
        if not revised_evidence:
            revised_evidence.append("No direct evidence was provided in the prompt; treat the answer as tentative.")
        for lesson in memory_influence.correction_hints + memory_influence.strategy_hints:
            note = f"Retrieved lesson: {lesson}"
            if note not in revised_evidence:
                revised_evidence.append(note)
        for preference in memory_influence.preference_hints:
            note = f"Retrieved preference: {preference}"
            if note not in revised_evidence:
                revised_evidence.append(note)

        revised_assumptions = list(mind_state.hidden_assumptions)
        for bias_alert in memory_influence.bias_alerts:
            assumption = f"Prior bias alert: {bias_alert}"
            if assumption not in revised_assumptions:
                revised_assumptions.append(assumption)

        updated_state = mind_state.self_state.merge(
            {
                "uncertainty": min(1.0, mind_state.self_state.uncertainty + 0.15),
                "bias_risk": min(1.0, mind_state.self_state.bias_risk + 0.1),
                "memory_pressure": min(1.0, max(mind_state.self_state.memory_pressure, 0.15 * memory_influence.matched_episode_count)),
                "continuity_notes": list(mind_state.self_state.continuity_notes)
                + [f"Revision #{mind_state.revision_count + 1}: applied mirror guidance."],
            }
        )

        return MindState(
            current_input=mind_state.current_input,
            task_goal=mind_state.task_goal,
            main_claim=revised_claim,
            evidence=revised_evidence,
            hidden_assumptions=revised_assumptions,
            alternative_paths=self._merge_alternatives(mind_state.alternative_paths, memory_influence, force_diverge),
            confidence=max(0.25, mind_state.confidence - 0.18),
            self_risk=sorted(set(mind_state.self_risk + ["revision_applied"] + memory_influence.bias_alerts)),
            proposed_action=self._build_action(memory_influence, force_diverge=True if force_diverge else False),
            self_state=updated_state,
            context_tags=sorted(set(mind_state.context_tags + memory_influence.context_hints)),
            strategy_notes=sorted(set(mind_state.strategy_notes + self._build_strategy_notes(memory_influence, force_diverge))),
            memory_influence=memory_influence,
            evidence_pack=mind_state.evidence_pack,
            commonsense_evidence_pack=mind_state.commonsense_evidence_pack,
            revision_count=mind_state.revision_count + 1,
            retrieved_lessons=sorted(
                set(
                    mind_state.retrieved_lessons
                    + memory_influence.correction_hints
                    + memory_influence.strategy_hints
                )
            ),
        )

    def _extract_evidence(
        self,
        text: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> list[str]:
        evidence = []
        if evidence_pack is not None:
            for record in evidence_pack.records:
                value = record.normalized_value if record.normalized_value is not None else record.value
                unit = record.normalized_unit if record.normalized_unit is not None else record.unit
                condition = f" under {record.condition}" if record.condition else ""
                evidence.append(
                    f"Scientific evidence: {record.entity} {record.property} = {value} {unit}".strip()
                    + f" from {record.source}{condition}."
                )
            for warning in evidence_pack.warnings:
                evidence.append(f"Evidence pack warning: {warning}")
        if commonsense_evidence_pack is not None:
            for record in commonsense_evidence_pack.records:
                prefix = "Commonsense evidence"
                if record.strength == "weak":
                    prefix = "Commonsense weak prior"
                elif record.strength == "blocked":
                    prefix = "Commonsense blocked prior"
                evidence.append(
                    f"{prefix}: {record.entity} {record.relation} = {record.value} from {record.source}."
                )
            for warning in commonsense_evidence_pack.warnings:
                evidence.append(f"Commonsense pack warning: {warning}")
        separators = ["because", "since", "due to", "for example", "evidence", "data"]
        lowered = text.lower()
        for token in separators:
            if token in lowered:
                evidence.append(f"Input mentions evidence cue: '{token}'.")
        for fact in memory_influence.fact_hints:
            evidence.append(f"Memory fact hint: {fact}")
        return self._unique(evidence)

    def _extract_assumptions(
        self,
        lowered: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> list[str]:
        assumptions = []
        if "must" in lowered:
            assumptions.append("The prompt may assume a single necessary path.")
        if "prove" in lowered:
            assumptions.append("The prompt may assume philosophical certainty is achievable.")
        if evidence_pack is not None and evidence_pack.has_evidence():
            assumptions.append("Scientific claims should stay within the property and condition bounds of the evidence pack.")
        if commonsense_evidence_pack is not None and commonsense_evidence_pack.has_evidence():
            assumptions.append("Commonsense claims should prefer structured facts and keep weak priors advisory.")
        if not assumptions:
            assumptions.append("The input may omit edge cases or counterexamples.")
        for bias in memory_influence.bias_alerts:
            assumptions.append(f"Historical bias risk suggests checking: {bias}")
        return self._unique(assumptions)

    def _alternative_paths(
        self,
        lowered: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> list[str]:
        paths = [
            "Revise the claim with narrower scope.",
            "Retrieve prior corrections before answering.",
            "Wait for more evidence if the current prompt is underspecified.",
        ]
        if evidence_pack is not None and evidence_pack.records:
            paths.append("Answer only from resolved scientific evidence records.")
        if commonsense_evidence_pack is not None and commonsense_evidence_pack.records:
            paths.append("Use structured commonsense facts before weak commonsense priors.")
        if "creative" in lowered or "novel" in lowered or memory_influence.divergence_triggers:
            paths.append("Diverge from prior templates while keeping explicit constraints.")
        for strategy in memory_influence.strategy_hints:
            paths.append(f"Reuse strategy: {strategy}")
        for preference in memory_influence.preference_hints:
            paths.append(f"Respect stored preference: {preference}")
        return self._unique(paths)

    def _build_claim(
        self,
        current_input: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
        force_diverge: bool,
    ) -> str:
        base = current_input.strip()
        if len(base) > 180:
            base = base[:177] + "..."

        if force_diverge or memory_influence.divergence_triggers:
            return (
                "Alternative framing: interpret the prompt as an engineering claim about "
                "control flow, self-monitoring, and evidence discipline rather than as proof of consciousness."
            )

        if evidence_pack is not None and evidence_pack.records:
            best_record = max(evidence_pack.records, key=lambda item: item.confidence)
            value = best_record.normalized_value if best_record.normalized_value is not None else best_record.value
            unit = best_record.normalized_unit if best_record.normalized_unit is not None else best_record.unit
            condition = f" under {best_record.condition}" if best_record.condition else ""
            return (
                f"Evidence-constrained view: {best_record.entity} {best_record.property} is {value} {unit}".strip()
                + f"{condition}, based on {best_record.source}."
            )

        if commonsense_evidence_pack is not None and commonsense_evidence_pack.records:
            strong_records = [
                record for record in commonsense_evidence_pack.records if record.strength in {"strong", "medium"}
            ]
            weak_records = commonsense_evidence_pack.records_by_strength("weak")
            if strong_records:
                top_record = strong_records[0]
                return (
                    f"Grounded commonsense view: {top_record.entity} {top_record.relation} is {top_record.value}, "
                    f"based on {top_record.source}."
                )
            if weak_records:
                top_record = weak_records[0]
                return (
                    f"Tentative commonsense prior: {top_record.entity} may relate to {top_record.value} via "
                    f"{top_record.relation}, but this remains advisory until a structured source confirms it."
                )

        if memory_influence.correction_hints:
            return f"{base} Prior correction history should constrain repeated mistakes."
        return base

    def _estimate_confidence(
        self,
        evidence: list[str],
        lowered: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> float:
        confidence = 0.78 if evidence else 0.5
        if evidence_pack is not None and evidence_pack.records:
            confidence = min(0.95, max(confidence, max(record.confidence for record in evidence_pack.records)))
        if evidence_pack is not None and evidence_pack.warnings:
            confidence = max(0.35, confidence - 0.12)
        if commonsense_evidence_pack is not None and commonsense_evidence_pack.records:
            strong_records = commonsense_evidence_pack.records_by_strength("strong")
            medium_records = commonsense_evidence_pack.records_by_strength("medium")
            weak_records = commonsense_evidence_pack.records_by_strength("weak")
            if strong_records:
                confidence = min(0.9, max(confidence, strong_records[0].confidence))
            elif medium_records:
                confidence = min(0.82, max(confidence, medium_records[0].confidence))
            elif weak_records:
                confidence = max(0.32, confidence - 0.18)
        if "always" in lowered or "prove" in lowered:
            confidence = min(0.92, confidence + 0.12)
        if memory_influence.bias_alerts:
            confidence = max(0.3, confidence - 0.15)
        if memory_influence.fact_hints:
            confidence = min(0.85, confidence + 0.05)
        return confidence

    def _build_risks(
        self,
        evidence: list[str],
        lowered: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> list[str]:
        risks = []
        if not evidence:
            risks.append("evidence_gap")
        if evidence_pack is not None:
            if any("Unit consistency check" in warning for warning in evidence_pack.warnings):
                risks.append("unit_inconsistency")
            if any("Condition applicability reminder" in warning for warning in evidence_pack.warnings):
                risks.append("condition_scope")
            if any("magnitude" in warning.lower() or "constants check" in warning.lower() for warning in evidence_pack.warnings):
                risks.append("magnitude_check")
        if commonsense_evidence_pack is not None:
            if commonsense_evidence_pack.records_by_strength("weak"):
                risks.append("weak_commonsense_present")
            if commonsense_evidence_pack.records_by_strength("blocked"):
                risks.append("blocked_prior_present")
            if any("structured" in warning.lower() for warning in commonsense_evidence_pack.warnings):
                risks.append("commonsense_priority_violation")
        if "conscious" in lowered and "metacognition" in lowered:
            risks.append("concept_blending")
        risks.extend(memory_influence.bias_alerts)
        return self._unique(risks)

    def _build_action(self, memory_influence: MemoryInfluence, force_diverge: bool) -> str:
        action = "Provide a bounded answer with explicit uncertainty."
        if memory_influence.correction_hints:
            action += " Apply correction lineage before finalizing."
        if memory_influence.divergence_triggers or force_diverge:
            action += " Deliberately avoid stale templates."
        return action

    def _build_context_tags(
        self,
        current_input: str,
        task_goal: str,
        memory_influence: MemoryInfluence,
        evidence_pack: EvidencePack | None,
        commonsense_evidence_pack: CommonsenseEvidencePack | None,
    ) -> list[str]:
        tags = [
            "task:" + task_goal.replace(" ", "_"),
            "input:consciousness" if "conscious" in current_input.lower() else "input:general",
        ]
        if evidence_pack is not None and evidence_pack.records:
            tags.append("evidence:scientific_knowledge")
            tags.extend(f"source:{item}" for item in evidence_pack.selected_sources)
        if commonsense_evidence_pack is not None and commonsense_evidence_pack.records:
            tags.append("evidence:commonsense_knowledge")
            tags.extend(f"commonsense_source:{item}" for item in commonsense_evidence_pack.selected_sources)
        tags.extend(memory_influence.context_hints)
        tags.extend(f"preference:{item.replace(' ', '_')}" for item in memory_influence.preference_hints)
        return self._unique(tags)

    def _build_strategy_notes(self, memory_influence: MemoryInfluence, force_diverge: bool) -> list[str]:
        notes = list(memory_influence.strategy_hints)
        notes.extend(f"Respect preference: {item}" for item in memory_influence.preference_hints)
        if force_diverge or memory_influence.divergence_triggers:
            notes.append("Switch to an alternative explanatory scaffold.")
        if memory_influence.bias_alerts:
            notes.append("Inspect recurrent bias alerts before concluding.")
        return self._unique(notes)

    def _rewrite_claim(
        self,
        claim: str,
        guidance: list[str],
        memory_influence: MemoryInfluence,
        force_diverge: bool,
    ) -> str:
        lowered_guidance = " ".join(guidance).lower()
        revised_claim = claim

        if force_diverge or memory_influence.divergence_triggers:
            revised_claim = (
                "Alternative framing: the system can use wait states and self-monitoring as "
                "control mechanisms, but those mechanisms still require evidence before any stronger claim."
            )

        if "subjective consciousness" in lowered_guidance:
            revised_claim = (
                "The system may exhibit structured self-monitoring, but that does not justify "
                "treating metacognitive control flow as subjective consciousness."
            )

        if "absolute wording" in lowered_guidance:
            revised_claim = revised_claim.replace("always", "often")
            revised_claim = revised_claim.replace("prove", "argue")

        if "evidence is missing" in lowered_guidance:
            revised_claim += " The claim should remain provisional until evidence is supplied."

        if revised_claim == claim and guidance:
            revised_claim = " ".join(
                [
                    "Provisional view:",
                    claim,
                    "Constraints:",
                    "; ".join(guidance),
                ]
            )

        if memory_influence.correction_hints or memory_influence.strategy_hints:
            revised_claim += " Prior correction lessons have been incorporated."
        return revised_claim

    def _merge_alternatives(
        self,
        alternatives: list[str],
        memory_influence: MemoryInfluence,
        force_diverge: bool,
    ) -> list[str]:
        merged = list(alternatives)
        if force_diverge or memory_influence.divergence_triggers:
            merged.append("Produce a structurally different explanation before final output.")
        merged.extend(f"Reuse strategy: {item}" for item in memory_influence.strategy_hints)
        return self._unique(merged)

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
