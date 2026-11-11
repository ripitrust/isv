"""The skills are the only writers of most events: an event no skill logs leaves its metric empty."""

import re
import unittest
from pathlib import Path

from isv import events

SKILLS = Path(__file__).resolve().parents[1] / "skills"
# Recorded by humans through `isv note`, not by a skill.
_CLI_ONLY = frozenset({"note"})


class SkillCoverageTest(unittest.TestCase):
    def test_every_event_is_logged_by_a_skill(self) -> None:
        text = "\n".join(p.read_text(encoding="utf-8") for p in SKILLS.glob("*/SKILL.md"))

        # The lookahead stops a prefix ("review") from matching a longer event ("review.round").
        missing = [
            e for e in events.EVENTS
            if e not in _CLI_ONLY and not re.search(rf"isv log {re.escape(e)}(?![\w.-])", text)
        ]

        self.assertEqual(missing, [])


class DecisionCardTest(unittest.TestCase):
    def test_frame_offers_explain_and_keeps_the_decision_open(self) -> None:
        # Explaining is not a teach-back: the card comes back and the decision stays open.
        text = (SKILLS / "frame" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("**Explain**", text)
        self.assertIn("stage=frame", text)
        self.assertIn("show the same card again", text)
        self.assertIn("An explanation is not a teach-back", text)
        self.assertIn("stays open", text)


if __name__ == "__main__":
    unittest.main()
