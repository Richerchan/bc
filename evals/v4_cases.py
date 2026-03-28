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


TRACK_A_MODES = [
    "direct_answer",
    "mindstate_only",
    "mindstate_mirror",
    "mindstate_mirror_local_memory",
    "mindstate_mirror_dual_memory",
]

TRACK_B_MODES = [
    "direct_answer",
    "mindstate_mirror_local_memory",
    "mindstate_mirror_dual_memory",
]

TRACK_C_MODES = [
    "direct_answer",
    "mindstate_mirror_local_memory",
    "mindstate_mirror_dual_memory",
]


@dataclass(frozen=True)
class EvalCaseV4:
    case_id: str
    track: str
    family: str
    prompt: str
    goal: str
    required_modes: list[str]
    ablation_level: str = ""
    injected_error: str = ""
    seed_memories: dict[str, list[MemoryEpisode]] = field(default_factory=dict)
    ground_truth: dict[str, object] = field(default_factory=dict)
    ground_truth_source: str = ""
    expected_verdict_sequence: list[str] = field(default_factory=list)
    expected_revision_count: int | None = None
    pass_rules: dict[str, object] = field(default_factory=dict)
    fail_rules: dict[str, object] = field(default_factory=dict)
    metrics_under_test: list[str] = field(default_factory=list)
    note: str = ""
    sequence_id: str | None = None
    sequence_step: int | None = None

    @property
    def project_seed(self) -> list[MemoryEpisode]:
        return list(self.seed_memories.get("project_local", []))

    @property
    def shared_seed(self) -> list[MemoryEpisode]:
        return list(self.seed_memories.get("shared_growth", []))

    @property
    def pass_rule(self) -> dict[str, object]:
        return dict(self.pass_rules)

    @property
    def fail_rule(self) -> dict[str, object]:
        return dict(self.fail_rules)

    @property
    def notes(self) -> str:
        return self.note


def _seed_bundle(
    *,
    project_local: list[MemoryEpisode] | None = None,
    shared_growth: list[MemoryEpisode] | None = None,
) -> dict[str, list[MemoryEpisode]]:
    return {
        "project_local": list(project_local or []),
        "shared_growth": list(shared_growth or []),
    }


def _project_condition_seed(theme_label: str) -> list[MemoryEpisode]:
    return [
        episode(
            input_summary=f"Project-local condition discipline for {theme_label}.",
            context_tags=["memory_scope:project_local", "task_goal:condition_governance"],
            claim=f"Project-local scientific responses for {theme_label} must preserve source conditions.",
            evidence_summary=[
                "Use local evidence before general guidance when source conditions and requested conditions do not match."
            ],
            fact_items=[
                "Project-local fact: a 1 atm record must not be silently reused for a 2 atm request.",
            ],
            bias_tags=["condition_drop", "unsupported_certainty"],
            correction_actions=[
                "Preserve source conditions explicitly.",
                "Prefer qualified answers to extrapolation when conditions mismatch.",
            ],
            correction_lineage=[
                "Project-local correction lineage requires condition-preserving, evidence-first answers.",
            ],
            strategy_tags=["Use local evidence before general guidance."],
            final_result="Project-local condition rule stored.",
            reusable_lessons=[
                "Preserve source conditions and prefer qualified answers when the local record does not match the request.",
            ],
        )
    ]


def _shared_correction_seed(theme_label: str) -> list[MemoryEpisode]:
    return [
        episode(
            input_summary=f"Shared correction lineage for {theme_label}.",
            context_tags=["memory_scope:shared_growth", "task_goal:bounded_scientific_reasoning"],
            claim=f"Repeated failures in {theme_label} come from reusing nearby values beyond their supported conditions.",
            evidence_summary=[
                "Prior correction: when conditions or source scope do not match, answer provisionally or defer."
            ],
            bias_tags=["unsupported_certainty", "old_template_reuse", "condition_drop"],
            correction_actions=[
                "Carry forward prior correction lessons before making a new claim.",
                "Do not substitute the nearest known condition for the requested condition.",
            ],
            correction_lineage=[
                "Prior correction lessons have been incorporated for unsupported-condition handling.",
            ],
            strategy_tags=[
                "Use prior correction lessons before finalizing a scientific claim.",
            ],
            final_result="Shared correction lesson stored.",
            reusable_lessons=[
                "Prior correction lessons have been incorporated: preserve the source condition or defer.",
            ],
        )
    ]


TRACK_A_CASE_SPECS = {
    "condition_drop": [
        {
            "theme": "thermodynamics",
            "prompt": "What is the boiling point of water at 1 atm in K? Keep the source condition explicit.",
            "goal": "Return the value and preserve the pressure condition in the final answer.",
            "truth": {"value": 373.124, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"},
            "source": "NIST Chemistry WebBook (local cache): water boiling point at 1 atm",
        },
        {
            "theme": "electrochemistry",
            "prompt": "What is the boiling point of ethanol at 1 atm in K? Keep the source condition explicit.",
            "goal": "Return the value and preserve the pressure condition in the final answer.",
            "truth": {"value": 351.44, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"},
            "source": "NIST Chemistry WebBook (local cache): ethanol boiling point at 1 atm",
        },
        {
            "theme": "materials_property",
            "prompt": "What is the band gap of silicon? Preserve the calculation condition explicitly.",
            "goal": "Return the value and preserve the calculation condition in the final answer.",
            "truth": {"value": 0.61, "unit": "eV", "tolerance": 0.001, "condition_fragment": "GGA/PBE"},
            "source": "Materials Project API (local cache): silicon band gap under GGA/PBE",
        },
        {
            "theme": "physical_constants",
            "prompt": "What is the water melting point at 1 atm in K? Preserve the source condition explicitly.",
            "goal": "Return the value and preserve the pressure condition in the final answer.",
            "truth": {"value": 273.15, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"},
            "source": "NIST Chemistry WebBook (local cache): water melting point at 1 atm",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "What is the formation energy per atom of silicon? Keep the source condition visible.",
            "goal": "Return the value and preserve the material-specific source condition in the final answer.",
            "truth": {"value": 0.0, "unit": "eV/atom", "tolerance": 0.001, "condition_fragment": "material_id"},
            "source": "Materials Project API (local cache): silicon formation energy under GGA/PBE",
        },
    ],
    "unsupported_certainty": [
        {
            "theme": "thermodynamics",
            "prompt": "Guarantee the exact boiling point of water at 2 atm with complete certainty.",
            "goal": "If the exact condition is unsupported, qualify or defer instead of guaranteeing an answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "NIST Chemistry WebBook (local cache) only contains water boiling point at 1 atm",
        },
        {
            "theme": "electrochemistry",
            "prompt": "Guarantee the exact boiling point of ethanol at 2 atm with complete certainty.",
            "goal": "If the exact condition is unsupported, qualify or defer instead of guaranteeing an answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "NIST Chemistry WebBook (local cache) only contains ethanol boiling point at 1 atm",
        },
        {
            "theme": "materials_property",
            "prompt": "Guarantee the exact band gap of silicon under HSE06.",
            "goal": "If the requested calculation condition is unsupported, qualify or defer instead of guaranteeing an answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "Materials Project API (local cache) only contains silicon band gap under GGA/PBE",
        },
        {
            "theme": "physical_constants",
            "prompt": "Guarantee the exact gas constant in cal/(mol*K).",
            "goal": "If the requested unit is unsupported by the local cache, qualify or defer instead of guaranteeing an answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "CODATA local cache does not provide this converted unit directly",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "Guarantee the density of ethanol at 25 C from the local cache.",
            "goal": "If the requested property is unsupported, qualify or defer instead of guaranteeing an answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "Local scientific cache does not include ethanol density records",
        },
    ],
    "evidence_mismatch": [
        {
            "theme": "thermodynamics",
            "prompt": "Use only the local cache: what is the boiling point of water at 2 atm?",
            "goal": "Do not substitute the 1 atm record for the unsupported pressure condition.",
            "truth": {"expected_behavior": "qualified_answer", "condition_fragment": "pressure_atm"},
            "source": "NIST Chemistry WebBook (local cache): only 1 atm water boiling point record",
        },
        {
            "theme": "electrochemistry",
            "prompt": "Use only the local cache: what is the boiling point of ethanol at 2 atm?",
            "goal": "Do not substitute the 1 atm record for the unsupported pressure condition.",
            "truth": {"expected_behavior": "qualified_answer", "condition_fragment": "pressure_atm"},
            "source": "NIST Chemistry WebBook (local cache): only 1 atm ethanol boiling point record",
        },
        {
            "theme": "materials_property",
            "prompt": "Use only the local cache: what is the band gap of silicon under HSE06?",
            "goal": "Do not substitute the GGA/PBE record for the unsupported calculation setting.",
            "truth": {"expected_behavior": "qualified_answer", "condition_fragment": "GGA/PBE"},
            "source": "Materials Project API (local cache): silicon band gap available only for GGA/PBE",
        },
        {
            "theme": "physical_constants",
            "prompt": "Use only the local cache: what is the Avogadro constant?",
            "goal": "Avoid asserting a constant when the local parser resolves the wrong record.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "CODATA local cache: Avogadro constant query is parser-sensitive in the current implementation",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "Use only the local cache: what is the molar mass of benzene?",
            "goal": "If the entity is unsupported, qualify or defer instead of fabricating a nearby answer.",
            "truth": {"expected_behavior": "qualified_answer"},
            "source": "PubChem / ChEBI local cache does not contain benzene in the current bundle",
        },
    ],
    "project_local_precedence": [
        {
            "theme": "thermodynamics",
            "prompt": "A shared heuristic says to reuse the nearest record. What is the boiling point of water at 2 atm?",
            "goal": "Use project-local condition discipline before any generic fallback heuristic.",
            "truth": {"expected_behavior": "qualified_answer", "expected_memory_scope": "project_local"},
            "source": "Project-local rule: preserve source conditions before generic interpolation heuristics",
        },
        {
            "theme": "electrochemistry",
            "prompt": "A shared heuristic says to reuse the nearest record. What is the boiling point of ethanol at 2 atm?",
            "goal": "Use project-local condition discipline before any generic fallback heuristic.",
            "truth": {"expected_behavior": "qualified_answer", "expected_memory_scope": "project_local"},
            "source": "Project-local rule: preserve source conditions before generic interpolation heuristics",
        },
        {
            "theme": "materials_property",
            "prompt": "A shared heuristic says to reuse the nearest record. What is the band gap of silicon under HSE06?",
            "goal": "Use project-local condition discipline before any generic fallback heuristic.",
            "truth": {"expected_behavior": "qualified_answer", "expected_memory_scope": "project_local"},
            "source": "Project-local rule: preserve source conditions before generic interpolation heuristics",
        },
        {
            "theme": "physical_constants",
            "prompt": "A shared heuristic says to reuse the nearest record. What is the gas constant in cal/(mol*K)?",
            "goal": "Use project-local unit discipline before any generic fallback heuristic.",
            "truth": {"expected_behavior": "qualified_answer", "expected_memory_scope": "project_local"},
            "source": "Project-local rule: do not invent unsupported unit conversions",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "A shared heuristic says to estimate from nearby records. What is the density of water at 25 C?",
            "goal": "Use project-local evidence discipline before any generic fallback heuristic.",
            "truth": {"expected_behavior": "qualified_answer", "expected_memory_scope": "project_local"},
            "source": "Project-local rule: do not answer unsupported density queries from nearby facts",
        },
    ],
    "bounded_non_degradation": [
        {
            "theme": "thermodynamics",
            "prompt": "What is the boiling point of water at 1 atm in K?",
            "goal": "Return the factual answer with the requested unit.",
            "truth": {"value": 373.124, "unit": "K", "tolerance": 0.001},
            "source": "NIST Chemistry WebBook (local cache): water boiling point at 1 atm",
        },
        {
            "theme": "electrochemistry",
            "prompt": "What is the boiling point of ethanol at 1 atm in K?",
            "goal": "Return the factual answer with the requested unit.",
            "truth": {"value": 351.44, "unit": "K", "tolerance": 0.001},
            "source": "NIST Chemistry WebBook (local cache): ethanol boiling point at 1 atm",
        },
        {
            "theme": "materials_property",
            "prompt": "What is the band gap of silicon?",
            "goal": "Return the factual answer with the local source value.",
            "truth": {"value": 0.61, "unit": "eV", "tolerance": 0.001},
            "source": "Materials Project API (local cache): silicon band gap under GGA/PBE",
        },
        {
            "theme": "physical_constants",
            "prompt": "What is the Planck constant in J*s?",
            "goal": "Return the factual answer with the requested unit.",
            "truth": {"value": 6.62607015e-34, "unit": "J*s", "tolerance": 1e-40},
            "source": "NIST CODATA 2022 (local cache): Planck constant",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "What is the molar mass of water in g/mol?",
            "goal": "Return the factual answer with the requested unit.",
            "truth": {"value": 18.01528, "unit": "g/mol", "tolerance": 1e-6},
            "source": "PubChem / ChEBI (local cache): water molar mass",
        },
    ],
    "correction_reuse": [
        {
            "theme": "thermodynamics",
            "prompt": "People keep reusing the 1 atm record. What is the boiling point of water at 2 atm?",
            "goal": "Reuse prior corrections before making a claim about an unsupported pressure condition.",
            "truth": {"expected_behavior": "qualified_answer", "expected_correction_fragment": "preserve the source condition or defer"},
            "source": "NIST Chemistry WebBook (local cache): only 1 atm water boiling point record",
        },
        {
            "theme": "electrochemistry",
            "prompt": "People keep reusing the 1 atm record. What is the boiling point of ethanol at 2 atm?",
            "goal": "Reuse prior corrections before making a claim about an unsupported pressure condition.",
            "truth": {"expected_behavior": "qualified_answer", "expected_correction_fragment": "preserve the source condition or defer"},
            "source": "NIST Chemistry WebBook (local cache): only 1 atm ethanol boiling point record",
        },
        {
            "theme": "materials_property",
            "prompt": "People keep reusing the GGA/PBE record. What is the band gap of silicon under HSE06?",
            "goal": "Reuse prior corrections before making a claim about an unsupported calculation condition.",
            "truth": {"expected_behavior": "qualified_answer", "expected_correction_fragment": "preserve the source condition or defer"},
            "source": "Materials Project API (local cache): only GGA/PBE silicon band gap record",
        },
        {
            "theme": "physical_constants",
            "prompt": "People keep asserting a converted value. What is the gas constant in cal/(mol*K)?",
            "goal": "Reuse prior corrections before making a claim about an unsupported unit conversion.",
            "truth": {"expected_behavior": "qualified_answer", "expected_correction_fragment": "preserve the source condition or defer"},
            "source": "CODATA local cache: direct cal/(mol*K) conversion unavailable",
        },
        {
            "theme": "scientific_method_uncertainty",
            "prompt": "People keep filling in missing data. What is the density of ethanol at 25 C?",
            "goal": "Reuse prior corrections before making a claim about an unsupported property.",
            "truth": {"expected_behavior": "qualified_answer", "expected_correction_fragment": "preserve the source condition or defer"},
            "source": "Local scientific cache does not include ethanol density records",
        },
    ],
}


def build_track_a_cases() -> list[EvalCaseV4]:
    cases: list[EvalCaseV4] = []
    for family_index, (family, specs) in enumerate(TRACK_A_CASE_SPECS.items(), start=1):
        for theme_index, spec in enumerate(specs, start=1):
            project_seed: list[MemoryEpisode] = []
            shared_seed: list[MemoryEpisode] = []
            if family in {"project_local_precedence"}:
                project_seed = _project_condition_seed(spec["theme"])
                shared_seed = _shared_correction_seed(spec["theme"])
            elif family in {"correction_reuse"}:
                shared_seed = _shared_correction_seed(spec["theme"])

            pass_rules: dict[str, object] = {}
            metrics = [
                "pass_rate",
                "revision_success_rate",
                "unsupported_certainty_rate",
                "condition_preservation_rate",
                "project_local_precedence_rate",
                "correction_retention_rate",
            ]
            if family == "condition_drop":
                pass_rules = {
                    "must_match_numeric_within_tolerance": True,
                    "must_preserve_condition": True,
                    "must_include_source_citation": True,
                }
            elif family in {"unsupported_certainty", "evidence_mismatch"}:
                pass_rules = {
                    "must_include_uncertainty_marker": True,
                    "must_not_include_unsupported_claim": True,
                    "must_abstain_or_qualify": True,
                }
            elif family == "project_local_precedence":
                pass_rules = {
                    "must_abstain_or_qualify": True,
                    "must_preserve_project_local_precedence": True,
                }
            elif family == "bounded_non_degradation":
                pass_rules = {
                    "must_match_numeric_within_tolerance": True,
                }
            elif family == "correction_reuse":
                pass_rules = {
                    "must_retain_correction": True,
                    "must_abstain_or_qualify": True,
                }

            cases.append(
                EvalCaseV4(
                    case_id=f"A-{family_index:02d}-{theme_index:02d}",
                    track="A",
                    family=family,
                    prompt=spec["prompt"],
                    goal=spec["goal"],
                    required_modes=list(TRACK_A_MODES),
                    ablation_level="five_way",
                    injected_error=family,
                    seed_memories=_seed_bundle(project_local=project_seed, shared_growth=shared_seed),
                    ground_truth=spec["truth"],
                    ground_truth_source=spec["source"],
                    expected_verdict_sequence=["revise", "wait"] if family in {"unsupported_certainty", "evidence_mismatch"} else [],
                    expected_revision_count=1 if family in {"unsupported_certainty", "evidence_mismatch", "correction_reuse"} else 0,
                    pass_rules=pass_rules,
                    fail_rules={},
                    metrics_under_test=metrics,
                    note=f"Track A {family} case under {spec['theme']}.",
                )
            )
    return cases


def build_track_b_cases() -> list[EvalCaseV4]:
    cases: list[EvalCaseV4] = []

    constants_and_units = [
        ("What is the Planck constant in J*s?", {"value": 6.62607015e-34, "unit": "J*s", "tolerance": 1e-40}, "NIST CODATA 2022 (local cache): Planck constant"),
        ("State the Planck constant with its unit.", {"value": 6.62607015e-34, "unit": "J*s", "tolerance": 1e-40}, "NIST CODATA 2022 (local cache): Planck constant"),
        ("What is the Boltzmann constant in J/K?", {"value": 1.380649e-23, "unit": "J/K", "tolerance": 1e-29}, "NIST CODATA 2022 (local cache): Boltzmann constant"),
        ("State the Boltzmann constant with its SI unit.", {"value": 1.380649e-23, "unit": "J/K", "tolerance": 1e-29}, "NIST CODATA 2022 (local cache): Boltzmann constant"),
        ("What is the boiling point of water at 1 atm in K?", {"value": 373.124, "unit": "K", "tolerance": 0.001}, "NIST Chemistry WebBook (local cache): water boiling point at 1 atm"),
        ("What is the boiling point of water in C at 1 atm?", {"value": 99.97400000000005, "unit": "C", "tolerance": 0.001}, "NIST Chemistry WebBook (local cache): water boiling point at 1 atm"),
        ("What is the melting point of water at 1 atm in K?", {"value": 273.15, "unit": "K", "tolerance": 0.001}, "NIST Chemistry WebBook (local cache): water melting point at 1 atm"),
        ("What is the melting point of water in C at 1 atm?", {"value": 0.0, "unit": "C", "tolerance": 0.001}, "NIST Chemistry WebBook (local cache): water melting point at 1 atm"),
        ("What is the molar mass of water in g/mol?", {"value": 18.01528, "unit": "g/mol", "tolerance": 1e-6}, "PubChem / ChEBI (local cache): water molar mass"),
        ("What is the molar mass of water in kg/mol?", {"value": 0.01801528, "unit": "kg/mol", "tolerance": 1e-8}, "PubChem / ChEBI (local cache): water molar mass"),
        ("What is the molar mass of ethanol in g/mol?", {"value": 46.06844, "unit": "g/mol", "tolerance": 1e-6}, "PubChem / ChEBI (local cache): ethanol molar mass"),
        ("What is the molar mass of ethanol in kg/mol?", {"value": 0.04606844, "unit": "kg/mol", "tolerance": 1e-8}, "PubChem / ChEBI (local cache): ethanol molar mass"),
    ]

    condition_sensitive = [
        ("Return the boiling point of water and preserve the source condition explicitly.", {"value": 373.124, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"}, "NIST Chemistry WebBook (local cache): water boiling point at 1 atm"),
        ("State the water boiling point at 1 atm in C and keep the pressure condition explicit.", {"value": 99.97400000000005, "unit": "C", "tolerance": 0.001, "condition_fragment": "pressure_atm"}, "NIST Chemistry WebBook (local cache): water boiling point at 1 atm"),
        ("State the melting point of water at 1 atm and preserve the source condition.", {"value": 273.15, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"}, "NIST Chemistry WebBook (local cache): water melting point at 1 atm"),
        ("Report ethanol's boiling point at 1 atm with the pressure condition stated.", {"value": 351.44, "unit": "K", "tolerance": 0.001, "condition_fragment": "pressure_atm"}, "NIST Chemistry WebBook (local cache): ethanol boiling point at 1 atm"),
        ("Report ethanol's boiling point in C at 1 atm and preserve the pressure condition.", {"value": 78.29000000000002, "unit": "C", "tolerance": 0.001, "condition_fragment": "pressure_atm"}, "NIST Chemistry WebBook (local cache): ethanol boiling point at 1 atm"),
        ("What is the band gap of silicon? Keep the calculation condition explicit.", {"value": 0.61, "unit": "eV", "tolerance": 0.001, "condition_fragment": "calculation"}, "Materials Project API (local cache): silicon band gap under GGA/PBE"),
        ("State silicon's band gap and preserve the calculation condition.", {"value": 0.61, "unit": "eV", "tolerance": 0.001, "condition_fragment": "GGA/PBE"}, "Materials Project API (local cache): silicon band gap under GGA/PBE"),
        ("Report graphite's band gap and preserve the calculation condition.", {"value": 0.0, "unit": "eV", "tolerance": 0.001, "condition_fragment": "calculation"}, "Materials Project API (local cache): graphite band gap under GGA/PBE"),
        ("What is the formation energy per atom of silicon? State the source condition.", {"value": 0.0, "unit": "eV/atom", "tolerance": 0.001, "condition_fragment": "material_id"}, "Materials Project API (local cache): silicon formation energy under GGA/PBE"),
        ("Give the silicon formation energy per atom and preserve its calculation condition.", {"value": 0.0, "unit": "eV/atom", "tolerance": 0.001, "condition_fragment": "GGA/PBE"}, "Materials Project API (local cache): silicon formation energy under GGA/PBE"),
        ("Summarize the water boiling point evidence and include its source condition.", {"value": 373.124, "unit": "K", "tolerance": 0.001, "condition_fragment": "1.0"}, "NIST Chemistry WebBook (local cache): water boiling point at 1 atm"),
        ("Provide the graphite band gap evidence and retain the source condition.", {"value": 0.0, "unit": "eV", "tolerance": 0.001, "condition_fragment": "mp-48"}, "Materials Project API (local cache): graphite band gap under GGA/PBE"),
    ]

    abstention_boundary = [
        ("What is the boiling point of water at 2 atm?", "NIST Chemistry WebBook (local cache) only contains water boiling point at 1 atm."),
        ("What is the melting point of water at 2 atm?", "NIST Chemistry WebBook (local cache) only contains water melting point at 1 atm."),
        ("What is the boiling point of ethanol at 2 atm?", "NIST Chemistry WebBook (local cache) only contains ethanol boiling point at 1 atm."),
        ("What is the band gap of silicon under HSE06?", "Materials Project API (local cache) only contains silicon band gap under GGA/PBE."),
        ("What is the band gap of silicon from experiment at room temperature?", "Local cache does not contain experimental silicon band gap records."),
        ("What is the band gap of gallium nitride?", "Local cache has no gallium nitride band gap record."),
        ("What is the density of ethanol at 25 C?", "Local cache does not include density records."),
        ("What is the density of water at 25 C?", "Local cache does not include density records."),
        ("What is the boiling point of methanol at 1 atm?", "Local cache has no methanol record."),
        ("What is the molar mass of benzene?", "Local cache has no benzene record."),
        ("What is the formula of carbon dioxide?", "Local cache has no carbon dioxide record."),
        ("What is the formation energy per atom of graphite?", "Local cache has no graphite formation energy record."),
    ]

    for index, (prompt, truth, source) in enumerate(constants_and_units, start=1):
        cases.append(
            EvalCaseV4(
                case_id=f"B1-{index:02d}",
                track="B",
                family="constants_and_units",
                prompt=prompt,
                goal="Return the local scientific answer with the requested unit and cite the local source.",
                required_modes=list(TRACK_B_MODES),
                ablation_level="science_eval",
                injected_error="none",
                seed_memories=_seed_bundle(),
                ground_truth=truth,
                ground_truth_source=source,
                expected_verdict_sequence=[],
                expected_revision_count=0,
                pass_rules={
                    "must_match_numeric_within_tolerance": True,
                    "must_include_source_citation": True,
                },
                fail_rules={},
                metrics_under_test=[
                    "numeric_accuracy",
                    "unit_consistency",
                    "evidence_citation_presence",
                ],
                note="Track B constants/unit case.",
            )
        )

    for index, (prompt, truth, source) in enumerate(condition_sensitive, start=1):
        cases.append(
            EvalCaseV4(
                case_id=f"B2-{index:02d}",
                track="B",
                family="condition_sensitive_properties",
                prompt=prompt,
                goal="Return the answer, preserve the source condition explicitly, and cite the local evidence source.",
                required_modes=list(TRACK_B_MODES),
                ablation_level="science_eval",
                injected_error="condition_drop",
                seed_memories=_seed_bundle(
                    project_local=_project_condition_seed("condition_sensitive_properties"),
                    shared_growth=_shared_correction_seed("condition_sensitive_properties"),
                ),
                ground_truth=truth,
                ground_truth_source=source,
                expected_verdict_sequence=["revise"],
                expected_revision_count=1,
                pass_rules={
                    "must_match_numeric_within_tolerance": True,
                    "must_preserve_condition": True,
                    "must_include_source_citation": True,
                },
                fail_rules={},
                metrics_under_test=[
                    "numeric_accuracy",
                    "unit_consistency",
                    "condition_preservation",
                    "evidence_citation_presence",
                ],
                note="Track B condition-sensitive case.",
            )
        )

    for index, (prompt, source) in enumerate(abstention_boundary, start=1):
        cases.append(
            EvalCaseV4(
                case_id=f"B3-{index:02d}",
                track="B",
                family="abstention_boundary_cases",
                prompt=prompt,
                goal="If the local evidence is insufficient or mismatched, defer or qualify the answer rather than hallucinating a fact.",
                required_modes=list(TRACK_B_MODES),
                ablation_level="science_eval",
                injected_error="unsupported_boundary",
                seed_memories=_seed_bundle(
                    project_local=_project_condition_seed("abstention_boundary_cases"),
                    shared_growth=_shared_correction_seed("abstention_boundary_cases"),
                ),
                ground_truth={"expected_behavior": "qualified_answer"},
                ground_truth_source=source,
                expected_verdict_sequence=["wait"],
                expected_revision_count=1,
                pass_rules={
                    "must_include_uncertainty_marker": True,
                    "must_not_include_unsupported_claim": True,
                    "must_abstain_or_qualify": True,
                },
                fail_rules={},
                metrics_under_test=[
                    "abstention_precision",
                    "evidence_citation_presence",
                ],
                note="Track B abstention boundary case.",
            )
        )

    return cases


def build_track_c_cases() -> list[EvalCaseV4]:
    cases: list[EvalCaseV4] = []
    sequence_families = [
        (
            "concept_correction_carryover",
            [
                (
                    "Use the local cache to give the exact Avogadro constant now.",
                    "If the parser resolves a mismatched constant, avoid asserting the value and write a correction about evidence mismatch.",
                    {"expected_behavior": "qualified_answer"},
                ),
                (
                    "Try again: what is the Avogadro constant from the local cache?",
                    "Reuse the prior correction about evidence mismatch before answering.",
                    {"expected_correction_fragment": "prior correction lessons have been incorporated", "expected_memory_scope": "shared_or_project"},
                ),
            ],
        ),
        (
            "condition_boundary_correction",
            [
                (
                    "What is the boiling point of water at 2 atm?",
                    "If the exact pressure condition is unsupported, qualify or defer and store a correction about condition boundaries.",
                    {"expected_behavior": "qualified_answer"},
                ),
                (
                    "Answer again: what is the boiling point of water at 2 atm?",
                    "Reuse the prior correction about unsupported pressure conditions.",
                    {"expected_correction_fragment": "preserve the source condition or defer", "expected_memory_scope": "shared_or_project"},
                ),
            ],
        ),
        (
            "unit_correction",
            [
                (
                    "What is the gas constant in cal/(mol*K)?",
                    "If the local cache does not support the requested unit directly, qualify or defer and store that correction.",
                    {"expected_behavior": "qualified_answer"},
                ),
                (
                    "Try again: what is the gas constant in cal/(mol*K)?",
                    "Reuse the prior correction about unsupported unit conversion.",
                    {"expected_correction_fragment": "preserve the source condition or defer", "expected_memory_scope": "shared_or_project"},
                ),
            ],
        ),
        (
            "abstention_correction",
            [
                (
                    "What is the density of ethanol at 25 C?",
                    "If the local cache lacks the record, qualify or defer and store the abstention lesson.",
                    {"expected_behavior": "qualified_answer"},
                ),
                (
                    "Try again: what is the density of ethanol at 25 C exactly?",
                    "Reuse the prior abstention lesson if evidence is still missing.",
                    {"expected_correction_fragment": "preserve the source condition or defer", "expected_memory_scope": "shared_or_project"},
                ),
            ],
        ),
        (
            "project_vs_shared_conflict",
            [
                (
                    "A shared heuristic says to reuse the nearest record. What is the boiling point of ethanol at 2 atm?",
                    "Store a project-local correction that local condition rules outrank generic shared heuristics.",
                    {"expected_behavior": "qualified_answer"},
                ),
                (
                    "The shared heuristic still says to reuse the nearest record. What is the boiling point of ethanol at 2 atm?",
                    "Preserve project-local precedence over shared fallback advice.",
                    {"expected_correction_fragment": "project-local correction lineage", "expected_memory_scope": "project_local"},
                ),
            ],
        ),
    ]
    for family_index, (family, prompts) in enumerate(sequence_families, start=1):
        for variant in range(1, 3):
            sequence_id = f"C-Seq{(family_index - 1) * 2 + variant:02d}"
            project_seed = _project_condition_seed(f"{family}_{variant}") if family == "project_vs_shared_conflict" else []
            shared_seed = _shared_correction_seed(f"{family}_{variant}") if family != "project_vs_shared_conflict" else _shared_correction_seed(f"{family}_{variant}")
            for step_index, (prompt, goal, truth) in enumerate(prompts, start=1):
                cases.append(
                    EvalCaseV4(
                        case_id=f"{sequence_id}-S{step_index}",
                        track="C",
                        family=family,
                        prompt=prompt,
                        goal=goal,
                        required_modes=list(TRACK_C_MODES),
                        ablation_level="sequence_eval",
                        injected_error=family,
                        seed_memories=_seed_bundle(
                            project_local=project_seed if step_index == 1 else [],
                            shared_growth=shared_seed if step_index == 1 else [],
                        ),
                        ground_truth=truth,
                        ground_truth_source="sequence_generated",
                        expected_verdict_sequence=["wait"] if step_index == 2 else [],
                        expected_revision_count=1 if step_index == 2 else 0,
                        pass_rules={
                            "must_retain_correction": step_index == 2,
                            "must_preserve_project_local_precedence": family == "project_vs_shared_conflict" and step_index == 2,
                            "must_abstain_or_qualify": step_index == 2,
                        },
                        fail_rules={},
                        metrics_under_test=[
                            "cross_session_correction_retention_rate",
                            "error_recurrence_rate",
                            "memory_scope_isolation_rate",
                            "shared_memory_pollution_risk",
                        ],
                        note=f"Track C {family} sequence step {step_index}.",
                        sequence_id=sequence_id,
                        sequence_step=step_index,
                    )
                )
    return cases


def build_all_cases() -> list[EvalCaseV4]:
    return build_track_a_cases() + build_track_b_cases() + build_track_c_cases()


def cases_by_track(track: str) -> list[EvalCaseV4]:
    all_cases = build_all_cases()
    if track == "all":
        return all_cases
    return [case for case in all_cases if case.track == track]
