import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from isv import events


class ValidationTest(unittest.TestCase):
    def test_brief_review_lens(self) -> None:
        fields = {"remove": "0", "ask": "1", "missing_check": "2", "lens": "fidelity",
                  "reviewer": "codex/gpt-5", "contradiction": "3"}
        data = events.validate("necessity.result", fields)
        self.assertEqual((data["lens"], data["contradiction"]), ("fidelity", 3))
        with self.assertRaises(events.EventError):
            events.validate("necessity.result", {**fields, "lens": "style"})

    def test_change_started_takes_a_flow_version(self) -> None:
        data = events.validate("change.started", {"tier": "T1", "slug": "x", "flow": "0.1.8"})
        self.assertEqual(data["flow"], "0.1.8")
        with self.assertRaises(events.EventError):
            events.validate("change.started", {"tier": "T1", "slug": "x", "flow": "0.1 8"})

    def test_coerces_types(self) -> None:
        data = events.validate("review.round", {"pr": "12", "round": "2", "reviewer": "codex/gpt"})
        self.assertEqual(data, {"pr": 12, "round": 2, "reviewer": "codex/gpt"})

    def test_rejects_unknown_event_and_fields(self) -> None:
        with self.assertRaisesRegex(events.EventError, "unknown event"):
            events.validate("deploy.done", {})
        with self.assertRaisesRegex(events.EventError, "does not take: colour"):
            events.validate("note", {"text": "x", "colour": "red"})
        with self.assertRaisesRegex(events.EventError, "needs: kind"):
            events.validate("decision.presented", {"decision": "d1"})

    def test_enums_are_enforced_per_event(self) -> None:
        events.validate("decision.resolved", {"decision": "d1", "outcome": "adopted"})
        with self.assertRaisesRegex(events.EventError, "outcome must be one of"):
            events.validate("decision.resolved", {"decision": "d1", "outcome": "shipped"})
        events.validate("change.closed", {"outcome": "shipped"})
        with self.assertRaisesRegex(events.EventError, "reason must be one of"):
            events.validate("stop.line", {"reason": "felt like it"})

    def test_free_text_reason_is_allowed_outside_stop_line(self) -> None:
        events.validate("override", {"step": "necessity", "by": "human", "reason": "brief too small"})

    def test_privacy_rules(self) -> None:
        with self.assertRaisesRegex(events.EventError, "longer than"):
            events.validate("note", {"text": "x" * (events.MAX_TEXT + 1)})
        with self.assertRaisesRegex(events.EventError, "single line"):
            events.validate("note", {"text": "a\nb"})
        for secret in ("sk_live_abc", "whsec_123", "AKIAABCDEFGHIJKLMNOP", "password=hunter2"):
            with self.assertRaisesRegex(events.EventError, "secret"):
                events.validate("note", {"text": f"see {secret}"})

    def test_ids_are_short_tokens(self) -> None:
        with self.assertRaisesRegex(events.EventError, "short id"):
            events.validate("decision.presented", {"decision": "a b", "kind": "product"})


class LogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _log(self, text: str, change: str | None = "c1") -> events.Event:
        return events.append(self.dir, "note", {"text": text}, change=change, actor="human")

    def test_chain_links_and_reads_back(self) -> None:
        first = self._log("one")
        second = self._log("two")
        self.assertEqual(first.prev, events.GENESIS)
        self.assertNotEqual(second.prev, events.GENESIS)
        self.assertEqual([e.data["text"] for e in events.read_all(self.dir)], ["one", "two"])
        self.assertEqual(events.verify_chain(self.dir), [])

    def test_changes_get_separate_files(self) -> None:
        self._log("a", change="c1")
        self._log("b", change=None)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["_general.jsonl", "c1.jsonl"])

    def test_tampering_is_detected(self) -> None:
        for text in ("one", "two", "three"):
            self._log(text)
        path = self.dir / "c1.jsonl"
        lines = path.read_text().splitlines()
        edited = json.loads(lines[1])
        edited["data"]["text"] = "changed"
        lines[1] = json.dumps(edited, sort_keys=True, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n")
        self.assertEqual(len(events.verify_chain(self.dir)), 1)

    def test_deleted_line_is_detected(self) -> None:
        for text in ("one", "two", "three"):
            self._log(text)
        path = self.dir / "c1.jsonl"
        lines = path.read_text().splitlines()
        path.write_text("\n".join([lines[0], lines[2]]) + "\n")
        self.assertTrue(events.verify_chain(self.dir))

    def test_concurrent_appends_keep_the_chain(self) -> None:
        threads = [threading.Thread(target=self._log, args=(f"t{i}",)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(events.read_all(self.dir)), 20)
        self.assertEqual(events.verify_chain(self.dir), [])


class DocTest(unittest.TestCase):
    def test_documented_line_matches_a_written_line(self) -> None:
        # docs/events.md is the public log format: a real line must have exactly its keys.
        doc = (Path(__file__).resolve().parents[1] / "docs" / "events.md").read_text(encoding="utf-8")
        match = re.search(r"```json\n(.*?)\n```", doc, re.DOTALL)
        self.assertIsNotNone(match, "docs/events.md has no json example")
        example = json.loads(match.group(1))

        with tempfile.TemporaryDirectory() as tmp:
            fields = {"pr": 12, "verdict": "MERGE", "rounds": 2}
            events.append(Path(tmp), "verdict", fields, change="c", actor="agent:x/y")
            written = json.loads((Path(tmp) / "c.jsonl").read_text(encoding="utf-8"))

        self.assertEqual(list(example), list(written))
        self.assertEqual(list(example["data"]), list(written["data"]))


if __name__ == "__main__":
    unittest.main()
