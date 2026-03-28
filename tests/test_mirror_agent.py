import unittest

from reflective_agent.mirror_agent import MirrorAgent
from reflective_agent.models import MindState, SelfState


def make_state(claim: str, evidence: list[str], confidence: float = 0.8) -> MindState:
    return MindState(
        current_input=claim,
        task_goal="test",
        main_claim=claim,
        evidence=evidence,
        hidden_assumptions=[],
        alternative_paths=["Alternative path"],
        confidence=confidence,
        self_risk=[],
        proposed_action="test",
        self_state=SelfState(active_goal="test"),
    )


class MirrorAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = MirrorAgent()

    def test_detects_overclaiming_and_evidence_gap(self) -> None:
        state = make_state("We can always prove the answer.", evidence=[], confidence=0.9)
        verdict = self.agent.review(state)
        self.assertIn("overclaiming", verdict.issues)
        self.assertIn("evidence_gap", verdict.issues)
        self.assertEqual(verdict.verdict, "revise")

    def test_detects_concept_blending_and_requests_retrieval(self) -> None:
        state = make_state(
            "Metacognition therefore proves consciousness.",
            evidence=["Input mentions evidence cue: 'because'."],
            confidence=0.8,
        )
        verdict = self.agent.review(state)
        self.assertIn("concept_blending", verdict.issues)
        self.assertEqual(verdict.verdict, "retrieve")

    def test_passes_bounded_claim_with_evidence(self) -> None:
        state = make_state(
            "The system may benefit from a mirror layer because it exposes evidence gaps.",
            evidence=["Input mentions evidence cue: 'because'."],
            confidence=0.6,
        )
        verdict = self.agent.review(state)
        self.assertEqual(verdict.verdict, "pass")
        self.assertEqual(verdict.issues, [])


if __name__ == "__main__":
    unittest.main()
