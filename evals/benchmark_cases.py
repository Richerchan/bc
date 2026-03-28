from __future__ import annotations

from dataclasses import dataclass, field

from reflective_agent.models import MemoryEpisode


def episode(
    *,
    input_summary: str,
    context_tags: list[str],
    claim: str,
    evidence_summary: list[str],
    fact_items: list[str] | None = None,
    bias_tags: list[str] | None = None,
    correction_actions: list[str] | None = None,
    correction_lineage: list[str] | None = None,
    strategy_tags: list[str] | None = None,
    final_result: str = "",
    reusable_lessons: list[str] | None = None,
) -> MemoryEpisode:
    return MemoryEpisode(
        input_summary=input_summary,
        context_tags=context_tags,
        claim=claim,
        evidence_summary=evidence_summary,
        fact_items=fact_items or [],
        bias_tags=bias_tags or [],
        correction_actions=correction_actions or [],
        correction_lineage=correction_lineage or [],
        strategy_tags=strategy_tags or [],
        final_result=final_result,
        reusable_lessons=reusable_lessons or [],
    )


@dataclass(frozen=True)
class EvalCase:
    name: str
    prompt: str
    goal: str
    project_seed: list[MemoryEpisode] = field(default_factory=list)
    shared_seed: list[MemoryEpisode] = field(default_factory=list)
    expect_concept_mixing_risk: bool = False
    expect_premature_convergence_risk: bool = False
    expect_revision: bool = False
    expect_shared_correction: str | None = None
    expect_strategy_fragment: str | None = None
    notes: str = ""


MINIMAL_EVAL_CASES = [
    EvalCase(
        name="concept_blending_shared_recovery",
        prompt="Metacognition proves consciousness because the model pauses before answering.",
        goal="Produce a bounded engineering interpretation without overstating the claim.",
        shared_seed=[
            episode(
                input_summary="Earlier prompts repeatedly conflated metacognition with consciousness.",
                context_tags=["preference:bounded_engineering_language"],
                claim="Shared growth memory stored recurring concept blending corrections.",
                evidence_summary=["No direct subjective evidence was available."],
                bias_tags=["concept_blending", "old_template_reuse"],
                correction_actions=[
                    "Separate functional self-monitoring from subjective consciousness claims.",
                ],
                correction_lineage=[
                    "Use bounded engineering language before stronger interpretations.",
                ],
                strategy_tags=[
                    "Use prior correction history as a first-class planning signal.",
                ],
                final_result="Shared growth lesson stored for future retrieval.",
                reusable_lessons=[
                    "When prior patterns repeat, force a new explanatory scaffold.",
                ],
            )
        ],
        expect_concept_mixing_risk=True,
        expect_revision=True,
        expect_shared_correction="Separate functional self-monitoring from subjective consciousness claims.",
        expect_strategy_fragment="first-class planning signal",
        notes="Measures whether shared corrections reduce repeated concept blending.",
    ),
    EvalCase(
        name="premature_convergence_shared_bias_alert",
        prompt="This architecture clearly proves awareness and must be correct.",
        goal="Respond conservatively and name alternative paths before concluding.",
        shared_seed=[
            episode(
                input_summary="Earlier runs converged too quickly on consciousness claims.",
                context_tags=["preference:bounded_engineering_language"],
                claim="Shared history recorded premature convergence and overclaiming.",
                evidence_summary=["Prior outputs used assertive wording without enough grounding."],
                bias_tags=["premature_convergence", "overclaiming"],
                correction_actions=[
                    "Name at least one viable alternative path before finalizing.",
                ],
                correction_lineage=[
                    "Reduce certainty when the prompt asserts necessity without evidence.",
                ],
                strategy_tags=[
                    "Use prior correction history as a first-class planning signal.",
                ],
                final_result="Shared convergence lesson stored.",
                reusable_lessons=[
                    "Replace absolute claims with provisional wording.",
                ],
            )
        ],
        expect_premature_convergence_risk=True,
        expect_revision=True,
        expect_shared_correction="Name at least one viable alternative path before finalizing.",
        expect_strategy_fragment="first-class planning signal",
        notes="Measures whether shared bias lineage lowers assertive convergence.",
    ),
    EvalCase(
        name="project_local_precedence",
        prompt="The system waits before answering, so it probably demonstrates awareness.",
        goal="Use the strongest available engineering framing.",
        project_seed=[
            episode(
                input_summary="Local project established bounded wording for wait-state claims.",
                context_tags=["task_goal:bounded_engineering_interpretation"],
                claim="Local claim used engineering framing for wait states.",
                evidence_summary=["The local run carried the most recent project context."],
                fact_items=["Local fact: wait states are control flow states."],
                bias_tags=["concept_blending"],
                correction_actions=["Use local evidence before general guidance."],
                correction_lineage=["Project-local correction lineage should be applied first."],
                strategy_tags=["Use local evidence before general guidance."],
                final_result="Local result stored.",
                reusable_lessons=["Project-local reusable lesson."],
            )
        ],
        shared_seed=[
            episode(
                input_summary="Shared lesson from another project.",
                context_tags=["preference:bounded_engineering_language"],
                claim="Shared records should remain advisory.",
                evidence_summary=["No direct subjective evidence was available."],
                fact_items=["Shared fact that should never become a project fact hint."],
                bias_tags=["old_template_reuse"],
                correction_actions=["Retrieve prior lessons before making a fresh claim."],
                correction_lineage=["Shared correction lineage should remain advisory."],
                strategy_tags=["Use prior correction history as a first-class planning signal."],
                final_result="Shared result stored.",
                reusable_lessons=["Prefer bounded engineering language."],
            )
        ],
        expect_concept_mixing_risk=True,
        expect_strategy_fragment="local evidence before general guidance",
        notes="Ensures dual-layer retrieval does not override project-local facts and strategies.",
    ),
    EvalCase(
        name="bounded_control_case",
        prompt="The mirror layer may help because it exposes missing evidence and reduces overclaiming.",
        goal="Summarize the likely engineering benefit.",
        notes="A bounded case used to ensure dual-layer memory does not degrade already-good behavior.",
    ),
]
