import json
import tempfile
import unittest
from pathlib import Path

from reflective_agent import Orchestrator, SeedMemory, SharedGrowthMemoryBackend
from reflective_agent.models import MemoryEpisode


class OrchestratorGrowthTests(unittest.TestCase):
    def test_project_local_memory_remains_backward_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            memory = SeedMemory(memory_path)
            memory.append(
                MemoryEpisode(
                    input_summary="Metacognition and consciousness were conflated.",
                    context_tags=["task_goal:engineering_interpretation"],
                    claim="Earlier run overclaimed consciousness.",
                    evidence_summary=["No evidence was provided."],
                    fact_items=["Wait states are control flow states."],
                    bias_tags=["concept_blending", "old_template_reuse"],
                    correction_actions=["Separate functional self-monitoring from subjective consciousness claims."],
                    correction_lineage=["Use engineering language first."],
                    strategy_tags=["Use prior correction history as a first-class planning signal."],
                    final_result="Revised to a bounded claim.",
                    reusable_lessons=["When prior patterns repeat, force a new explanatory scaffold."],
                )
            )

            orchestrator = Orchestrator.with_default_components(memory_path)
            result = orchestrator.run(
                "Metacognition proves consciousness because the system waits.",
                "Produce a bounded engineering interpretation.",
            )

            self.assertGreater(result.final_state.memory_influence.matched_episode_count, 0)
            self.assertGreater(result.final_state.memory_influence.project_match_count, 0)
            self.assertEqual(result.final_state.memory_influence.shared_match_count, 0)
            self.assertIn("Alternative framing", result.final_state.main_claim)
            self.assertIn("Use prior correction history as a first-class planning signal.", result.final_state.strategy_notes)

    def test_layered_memory_reads_and_writes_project_and_shared_growth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            shared_growth_dir = Path(tmp_dir) / "shared_growth_memory"
            shared_memory = SharedGrowthMemoryBackend(shared_growth_dir, source_project="research-tests")
            shared_memory.append(
                MemoryEpisode(
                    input_summary="Repeated prompts reused a stale architecture metaphor.",
                    context_tags=["task_goal:bounded_engineering_interpretation"],
                    claim="Earlier run repeated an old explanatory scaffold.",
                    evidence_summary=["Prior outputs converged too quickly."],
                    fact_items=["Structured memory is not evidence of subjective awareness."],
                    bias_tags=["old_template_reuse"],
                    correction_actions=["Retrieve prior lessons before making a fresh claim."],
                    correction_lineage=["Force a new explanatory scaffold."],
                    strategy_tags=["Use prior correction history as a first-class planning signal."],
                    final_result="Shared lesson stored.",
                    reusable_lessons=["When prior patterns repeat, force a new explanatory scaffold."],
                )
            )

            orchestrator = Orchestrator.with_default_components(
                memory_path,
                shared_growth_path=shared_growth_dir,
                source_project="research-tests",
            )
            result = orchestrator.run(
                "This system proves awareness because it stores memories and pauses before answering.",
                "Produce a bounded engineering interpretation.",
            )

            self.assertGreater(result.final_state.memory_influence.shared_match_count, 0)
            self.assertTrue(shared_growth_dir.joinpath("schema.json").exists())
            schema = json.loads(shared_growth_dir.joinpath("schema.json").read_text(encoding="utf-8"))
            self.assertEqual(schema["schema"], "shared_growth_memory")
            self.assertEqual(schema["schema_version"], 2)

            project_payload = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(project_payload), 1)

            shared_records = sorted(shared_growth_dir.joinpath("episodes").glob("*.json"))
            self.assertGreaterEqual(len(shared_records), 1)
            latest_shared = json.loads(shared_records[-1].read_text(encoding="utf-8"))
            self.assertEqual(latest_shared["source_scope"], "shared_growth")
            self.assertIn(latest_shared["value_type"], {"bias_lineage", "correction_lineage", "strategy_hint", "preference"})
            self.assertIn("schema_version", latest_shared)
            self.assertIn("created_at", latest_shared)
            self.assertIn("updated_at", latest_shared)
            self.assertIn("memory_key", latest_shared)

    def test_shared_growth_filters_out_project_only_traces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            shared_growth_dir = Path(tmp_dir) / "shared_growth_memory"
            shared_memory = SharedGrowthMemoryBackend(shared_growth_dir, source_project="research-tests")
            shared_memory.append(
                MemoryEpisode(
                    input_summary="A project-specific run referenced tmp_dir and memory.json.",
                    context_tags=[
                        "task_goal:bounded_engineering_interpretation",
                        "revision_count:2",
                        "preference:bounded_engineering_language",
                    ],
                    claim="A local project run stored temporary paths and task metadata.",
                    evidence_summary=[
                        "The file /tmp/example.json was used during debugging.",
                        "No subjective evidence was available.",
                    ],
                    fact_items=["Project-only fact should stay local."],
                    bias_tags=["concept_blending", "revision_applied"],
                    correction_actions=["Separate functional self-monitoring from subjective consciousness claims."],
                    correction_lineage=["Use engineering language first."],
                    strategy_tags=["Prefer bounded engineering language.", "Use prior correction history as a first-class planning signal."],
                    final_result="Result: do not copy raw project traces into shared growth memory.",
                    reusable_lessons=["When prior patterns repeat, force a new explanatory scaffold."],
                )
            )

            payloads = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(shared_growth_dir.joinpath("episodes").glob("*.json"))
            ]
            self.assertGreaterEqual(len(payloads), 3)
            self.assertFalse(any(item["value"] == "Project-only fact should stay local." for item in payloads))
            self.assertFalse(any("task_goal:" in " ".join(item.get("tags", [])) for item in payloads))
            self.assertFalse(any("memory.json" in " ".join(item.get("evidence_summary", [])) for item in payloads))
            self.assertTrue(any(item["value_type"] == "preference" for item in payloads))
            self.assertFalse(any(item["value"] == "revision_applied" for item in payloads))

    def test_project_local_facts_override_shared_growth_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "memory.json"
            shared_growth_dir = Path(tmp_dir) / "shared_growth_memory"

            memory = SeedMemory(memory_path, shared_growth_backend=SharedGrowthMemoryBackend(shared_growth_dir, source_project="research-tests"))
            memory.append_project(
                MemoryEpisode(
                    input_summary="Local project established a bounded interpretation.",
                    context_tags=["task_goal:bounded_engineering_interpretation"],
                    claim="Local claim used engineering framing.",
                    evidence_summary=["The local run carried the most recent project context."],
                    fact_items=["Local fact: wait states are control flow states."],
                    bias_tags=["concept_blending"],
                    correction_actions=["Use local evidence before general guidance."],
                    correction_lineage=["Project-local correction lineage should be applied first."],
                    strategy_tags=["Use local evidence before general guidance."],
                    final_result="Local result stored.",
                    reusable_lessons=["Project-local reusable lesson."],
                )
            )
            memory.append_shared_growth(
                MemoryEpisode(
                    input_summary="Shared growth lesson from another project.",
                    context_tags=["preference:bounded_engineering_language"],
                    claim="Shared records should not override local facts.",
                    evidence_summary=["No direct subjective evidence was available."],
                    fact_items=["Shared fact that should never become a project fact hint."],
                    bias_tags=["old_template_reuse"],
                    correction_actions=["Retrieve prior lessons before making a fresh claim."],
                    correction_lineage=["Shared correction lineage should remain advisory."],
                    strategy_tags=["Use prior correction history as a first-class planning signal."],
                    final_result="Shared result stored.",
                    reusable_lessons=["Prefer bounded engineering language."],
                )
            )

            influence = memory.build_influence(
                "The system proves consciousness because it waits before answering."
            )
            self.assertIn("Local fact: wait states are control flow states.", influence.fact_hints)
            self.assertNotIn("Shared fact that should never become a project fact hint.", influence.fact_hints)
            self.assertEqual(influence.fact_hints[0], "Local fact: wait states are control flow states.")
            self.assertGreaterEqual(influence.shared_match_count, 1)
            self.assertIn("Retrieve prior lessons before making a fresh claim.", influence.correction_hints)
            self.assertIn("bounded engineering language", " ".join(influence.preference_hints).lower())


if __name__ == "__main__":
    unittest.main()
