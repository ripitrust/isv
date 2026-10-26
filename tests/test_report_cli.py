import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from isv import cli, events, report


def _log(directory: Path, event: str, change: str = "c1", **fields: object) -> None:
    events.append(directory, event, dict(fields), change=change, actor="agent:test/model")


class ReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_metrics(self) -> None:
        _log(self.dir, "change.started", tier="T2", slug="ledger")
        # A T1 change never reaches frame, so it must not dilute human decisions per change.
        _log(self.dir, "change.started", change="c2", tier="T1", slug="fix")
        _log(self.dir, "decision.presented", decision="d1", kind="one-way")
        _log(self.dir, "decision.presented", decision="d2", kind="reversible")
        _log(self.dir, "decision.resolved", decision="d1", outcome="ruled", teachback="pass")
        _log(self.dir, "decision.resolved", decision="d2", outcome="agent-decided")
        _log(self.dir, "explain.requested", target="ledger", stage="frame")
        _log(self.dir, "review.round", pr=7, round=1, reviewer="codex", important=2, nit=2, removal=1)
        _log(self.dir, "review.round", pr=7, round=2, reviewer="codex", important=0)
        _log(self.dir, "finding.resolved", pr=7, finding="f1", response="fixed")
        _log(self.dir, "finding.resolved", pr=7, finding="f2", response="wrong")
        _log(self.dir, "verdict", pr=7, verdict="NEEDS-HUMAN", rounds=2)
        _log(self.dir, "override", step="necessity", by="human", reason="tiny brief")

        built = report.build(events.read_all(self.dir))
        self.assertEqual(built.changes_by_tier["T2"], 1)
        self.assertEqual(built.human_decisions_per_change, 1.0)
        self.assertEqual(built.teachback_first_pass, 1.0)
        self.assertEqual(built.explain_per_change, 0.5)
        self.assertEqual(built.rounds_per_pr, 2)
        self.assertEqual(built.reviewer_precision, 0.5)
        self.assertEqual(built.removal_share, 0.25)
        self.assertEqual(built.overrides["necessity"], 1)
        self.assertIn("Reviewer precision", report.render(built))

    def test_empty_log_renders(self) -> None:
        self.assertIn("n/a", report.render(report.build([])))


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ISV_LOG_DIR"] = self.tmp.name

    def tearDown(self) -> None:
        os.environ.pop("ISV_LOG_DIR", None)
        self.tmp.cleanup()

    def _run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_log_trace_verify(self) -> None:
        self.assertEqual(self._run("log", "change.started", "--change", "c9", "tier=T1", "slug=x")[0], 0)
        self.assertEqual(self._run("note", "brief felt long", "--change", "c9")[0], 0)
        code, out = self._run("trace", "c9")
        self.assertEqual(code, 0)
        self.assertIn("change.started", out)
        self.assertIn("[human]", out)
        self.assertEqual(self._run("verify-log")[0], 0)

    def test_fields_on_both_sides_of_an_option(self) -> None:
        # Some argparse versions stop collecting `fields` at the first option.
        code, _ = self._run("log", "verdict", "pr=1", "--change", "c9", "verdict=MERGE", "rounds=1")
        self.assertEqual(code, 0)
        self.assertIn("verdict", self._run("trace", "c9")[1])

    def test_unknown_option_is_still_rejected(self) -> None:
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            self._run("log", "verdict", "--chnage", "c9", "pr=1", "verdict=MERGE", "rounds=1")
        self.assertEqual(raised.exception.code, 2)

    def test_invalid_event_is_rejected(self) -> None:
        self.assertEqual(self._run("log", "verdict", "pr=1", "verdict=SHIP", "rounds=1")[0], 1)

    def test_templates_print(self) -> None:
        for name in cli.TEMPLATES:
            code, out = self._run("template", name)
            self.assertEqual(code, 0)
            self.assertTrue(out.strip())


if __name__ == "__main__":
    unittest.main()
