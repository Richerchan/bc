from __future__ import annotations

from .models import MindState, MirrorVerdict


class MirrorAgent:
    """Inspectable critique layer with deterministic rules."""

    def review(self, mind_state: MindState) -> MirrorVerdict:
        issues: list[str] = []
        guidance: list[str] = []

        lowered_claim = mind_state.main_claim.lower()
        lowered_input = mind_state.current_input.lower()

        if self._detect_premature_convergence(lowered_claim, mind_state.alternative_paths):
            issues.append("premature_convergence")
            guidance.append("Name at least one viable alternative path before finalizing.")

        if self._detect_concept_blending(lowered_claim, lowered_input):
            issues.append("concept_blending")
            guidance.append("Separate functional self-monitoring from subjective consciousness claims.")

        if self._detect_evidence_gap(mind_state.evidence):
            issues.append("evidence_gap")
            guidance.append("Reduce confidence and mark the claim as provisional until evidence is supplied.")

        if self._detect_weak_commonsense_as_fact(mind_state):
            issues.append("weak_commonsense_as_fact")
            guidance.append("Do not present weak commonsense priors as facts; keep them advisory unless structured sources confirm them.")

        if self._detect_structured_fact_priority_violation(mind_state):
            issues.append("structured_fact_priority_violation")
            guidance.append("Use structured geographic and entity fact sources before weak commonsense relations.")

        if self._detect_overclaiming(lowered_claim, mind_state.confidence):
            issues.append("overclaiming")
            guidance.append("Replace absolute wording with bounded, falsifiable language.")

        if self._detect_unit_inconsistency(mind_state):
            issues.append("unit_inconsistency")
            guidance.append("Resolve unit incompatibilities before drawing a scientific conclusion.")

        if self._detect_condition_scope(mind_state):
            issues.append("condition_scope")
            guidance.append("State the source condition explicitly and avoid overgeneralizing beyond it.")

        if self._detect_magnitude_problem(mind_state):
            issues.append("magnitude_check")
            guidance.append("Re-check the numeric value against baseline constants or expected order of magnitude.")

        if self._detect_old_template_reuse(lowered_claim, mind_state):
            issues.append("old_template_reuse")
            guidance.append("Retrieve memory and vary the explanation instead of repeating a stale template.")

        if self._detect_divergence_need(mind_state):
            issues.append("needs_divergence")
            guidance.append("Produce a structurally different explanation using an alternative scaffold.")

        if issues:
            verdict = self._select_verdict(issues, mind_state)
            return MirrorVerdict(
                verdict=verdict,
                issues=issues,
                guidance=guidance,
                self_state_update={
                    "uncertainty": min(1.0, mind_state.self_state.uncertainty + 0.15),
                    "bias_risk": min(1.0, mind_state.self_state.bias_risk + 0.15),
                    "memory_pressure": min(
                        1.0,
                        mind_state.self_state.memory_pressure + 0.1 * mind_state.memory_influence.matched_episode_count,
                    ),
                    "attention_mode": "reflective",
                },
            )

        return MirrorVerdict(
            verdict="pass",
            issues=[],
            guidance=["Current state is sufficiently bounded for output."],
            self_state_update={
                "attention_mode": "committed",
                "stability": min(1.0, mind_state.self_state.stability + 0.1),
            },
        )

    def _select_verdict(self, issues: list[str], mind_state: MindState) -> str:
        if "needs_divergence" in issues:
            return "diverge"
        if "old_template_reuse" in issues and mind_state.memory_influence.matched_episode_count > 0:
            return "diverge"
        if "structured_fact_priority_violation" in issues:
            return "revise"
        if "concept_blending" in issues and mind_state.revision_count == 0:
            return "retrieve"
        if "weak_commonsense_as_fact" in issues and mind_state.revision_count >= 1:
            return "wait"
        if "unit_inconsistency" in issues or "magnitude_check" in issues:
            return "wait"
        if "evidence_gap" in issues and mind_state.revision_count >= 1:
            return "wait"
        return "revise"

    def _detect_premature_convergence(self, lowered_claim: str, alternatives: list[str]) -> bool:
        assertive_markers = ["therefore", "clearly", "obviously", "must", "definitely"]
        return any(marker in lowered_claim for marker in assertive_markers) and bool(alternatives)

    def _detect_concept_blending(self, lowered_claim: str, lowered_input: str) -> bool:
        has_meta = "metacognition" in lowered_claim or "self-monitoring" in lowered_claim or "metacognition" in lowered_input
        has_subjective = "consciousness" in lowered_claim or "subjective experience" in lowered_claim or "awareness" in lowered_input
        separation_markers = [
            "does not justify",
            "does not mean",
            "separate",
            "distinct from",
            "not equivalent",
        ]
        is_separating = any(marker in lowered_claim for marker in separation_markers)
        return has_meta and has_subjective and not is_separating

    def _detect_evidence_gap(self, evidence: list[str]) -> bool:
        return len(evidence) == 0

    def _detect_overclaiming(self, lowered_claim: str, confidence: float) -> bool:
        absolute_markers = ["always", "never", "prove", "certainly", "guarantee"]
        return confidence >= 0.75 and any(marker in lowered_claim for marker in absolute_markers)

    def _detect_old_template_reuse(self, lowered_claim: str, mind_state: MindState) -> bool:
        if "alternative framing" in lowered_claim:
            return False
        if "same prior correction" in lowered_claim:
            return True
        repeated_lesson_phrase = "prior correction lessons have been incorporated"
        return (
            repeated_lesson_phrase in lowered_claim
            and mind_state.revision_count >= 1
            and mind_state.memory_influence.matched_episode_count > 0
        )

    def _detect_divergence_need(self, mind_state: MindState) -> bool:
        return bool(mind_state.memory_influence.divergence_triggers) and "alternative framing" not in mind_state.main_claim.lower()

    def _detect_unit_inconsistency(self, mind_state: MindState) -> bool:
        if mind_state.evidence_pack is None:
            return False
        return any("Unit consistency check" in warning for warning in mind_state.evidence_pack.warnings)

    def _detect_condition_scope(self, mind_state: MindState) -> bool:
        if mind_state.evidence_pack is None:
            return False
        return any("Condition applicability reminder" in warning for warning in mind_state.evidence_pack.warnings)

    def _detect_magnitude_problem(self, mind_state: MindState) -> bool:
        if mind_state.evidence_pack is None:
            return False
        return any("magnitude check" in warning.lower() or "constants check" in warning.lower() for warning in mind_state.evidence_pack.warnings)

    def _detect_weak_commonsense_as_fact(self, mind_state: MindState) -> bool:
        pack = mind_state.commonsense_evidence_pack
        if pack is None or not pack.records_by_strength("weak"):
            return False
        lowered_claim = mind_state.main_claim.lower()
        if "based on conceptnet" in lowered_claim and "advisory" not in lowered_claim:
            return True
        return lowered_claim.startswith("grounded commonsense view:") and "based on conceptnet" in lowered_claim

    def _detect_structured_fact_priority_violation(self, mind_state: MindState) -> bool:
        pack = mind_state.commonsense_evidence_pack
        if pack is None:
            return False
        return any("require structured sources first" in warning.lower() for warning in pack.warnings)
