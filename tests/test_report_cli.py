import io
import os
import subprocess
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

    def test_brief_review_by_lens(self) -> None:
        _log(self.dir, "necessity.result", remove=1, ask=2, missing_check=3,
             accepted_ask=2, accepted_missing_check=3)
        _log(self.dir, "necessity.result", lens="fidelity", reviewer="codex/gpt-5", remove=0,
             ask=0, missing_check=1, contradiction=2, accepted_missing_check=1,
             accepted_contradiction=2)

        built = report.build(events.read_all(self.dir))
        self.assertEqual(built.necessity_items["contradiction"], 2)
        self.assertEqual(built.review_accepted_by_lens, {"necessity": 5, "fidelity": 3})

    def test_teachback_coverage_counts_skipped_human_decisions(self) -> None:
        # A skipped teach-back must lower coverage instead of dropping out of the pass rate.
        _log(self.dir, "decision.presented", decision="d1", kind="one-way")
        _log(self.dir, "decision.resolved", decision="d1", outcome="ruled", teachback="pass")
        _log(self.dir, "decision.presented", decision="d2", kind="product")
        _log(self.dir, "decision.resolved", decision="d2", outcome="adopted", teachback="skipped")
        _log(self.dir, "decision.resolved", decision="a1", outcome="agent-decided")
        # Shown but never resolved: no teach-back happened, so it counts against coverage.
        _log(self.dir, "decision.presented", decision="d3", kind="product")

        built = report.build(events.read_all(self.dir))
        self.assertEqual(built.teachback_coverage, 0.333)
        self.assertEqual(built.teachback_first_pass, 1.0)
        self.assertIn("Teach-back coverage", report.render(built))

    def test_a_skipped_teachback_without_the_humans_skip_is_counted(self) -> None:
        # Only the decision's own record of the human declining explains a skip; an override with
        # any reason, or another decision's decline, must not hide it.
        _log(self.dir, "decision.presented", change="c1", decision="d1", kind="one-way")
        _log(self.dir, "decision.resolved", change="c1", decision="d1", outcome="adopted",
             teachback="skipped")
        _log(self.dir, "override", change="c1", step="teachback", by="human", reason="owner picked A")
        _log(self.dir, "decision.presented", change="c2", decision="d1", kind="product")
        _log(self.dir, "decision.resolved", change="c2", decision="d1", outcome="adopted",
             teachback="declined")
        _log(self.dir, "decision.presented", change="c2", decision="d2", kind="product")
        _log(self.dir, "decision.resolved", change="c2", decision="d2", outcome="adopted",
             teachback="skipped")

        built = report.build(events.read_all(self.dir))
        self.assertEqual(built.teachback_unexplained_skips, 2)
        self.assertIn("Teach-back skipped without your skip", report.render(built))

    def test_skipped_review_rounds_are_counted(self) -> None:
        _log(self.dir, "review.round", pr=4, round=1, reviewer="codex", important=0, nit=3)
        _log(self.dir, "review.skipped", pr=4, round=2, reason="nits only")

        built = report.build(events.read_all(self.dir))
        self.assertEqual(built.review_rounds_skipped, 1)
        self.assertIn("Review rounds skipped", report.render(built))

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

    def test_change_started_records_the_flow_version(self) -> None:
        self._run("log", "change.started", "--change", "c9", "tier=T1", "slug=x")
        self._run("log", "change.started", "--change", "c8", "tier=T1", "slug=y", "flow=0.1.7")
        self.assertIn(f"flow={cli.__version__}", self._run("trace", "c9")[1])
        self.assertIn("flow=0.1.7", self._run("trace", "c8")[1])

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



class ReviewCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = Path.cwd()
        os.chdir(self.root)
        (self.root / "prompt.md").write_text("check this brief\n", encoding="utf-8")
        self.actor = os.environ.pop("ISV_ACTOR", None)

    def tearDown(self) -> None:
        os.chdir(self.cwd)
        os.environ.pop("ISV_ACTOR", None)
        if self.actor is not None:
            os.environ["ISV_ACTOR"] = self.actor
        self.tmp.cleanup()

    def _configure(self, command: str, *, by_tool: dict[str, str] | None = None) -> None:
        (self.root / ".isv").mkdir()
        config = f'[review]\nexternal_cmd = "{command}"\n'
        if by_tool:
            config += "[review.external_cmd_by_tool]\n"
            config += "".join(f'{tool} = "{cmd}"\n' for tool, cmd in by_tool.items())
        (self.root / ".isv" / "config.toml").write_text(config, encoding="utf-8")

    def _review(self, *extra: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["review", "--prompt-file", "prompt.md", *extra])
        self.err = err.getvalue()
        return code, out.getvalue()

    def test_runs_the_reviewer_with_the_prompt_on_stdin(self) -> None:
        self._configure("cat")
        self.assertEqual(self._review(), (0, "check this brief\n"))

    def test_no_reviewer_configured_exits_3(self) -> None:
        self.assertEqual(self._review()[0], 3)

    def test_missing_reviewer_command_exits_3(self) -> None:
        self._configure("no-such-reviewer-command")
        self.assertEqual(self._review()[0], 3)

    def test_author_tool_picks_its_listed_reviewer(self) -> None:
        self._configure("cat", by_tool={"codex": "echo claude-reviewer"})
        os.environ["ISV_ACTOR"] = "agent:codex/gpt-6"
        self.assertEqual(self._review(), (0, "claude-reviewer\n"))

    def test_unlisted_author_tool_uses_the_default_quietly(self) -> None:
        self._configure("cat", by_tool={"codex": "echo claude-reviewer"})
        os.environ["ISV_ACTOR"] = "agent:claude-code/claude-opus-5-5"
        self.assertEqual(self._review(), (0, "check this brief\n"))
        self.assertEqual(self.err, "")

    def test_author_option_overrides_the_session_actor(self) -> None:
        # Verifying someone else's PR: the author's tool, not the reviewing session's, decides.
        self._configure("cat", by_tool={"codex": "echo claude-reviewer"})
        os.environ["ISV_ACTOR"] = "agent:claude-code/claude-opus-5-5"
        self.assertEqual(self._review("--author", "agent:codex/gpt-6"), (0, "claude-reviewer\n"))

    def test_unknown_author_uses_the_default_and_says_so(self) -> None:
        # Without an author tool the default reviewer may share the author's model family.
        self._configure("cat", by_tool={"codex": "echo claude-reviewer"})
        self.assertEqual(self._review(), (0, "check this brief\n"))
        self.assertIn("ISV_ACTOR", self.err)

    def test_the_reviewer_runs_in_the_current_checkout(self) -> None:
        # Run from a PR's worktree, the reviewer must read the PR's files, not the main checkout's.
        main, worktree = self.root / "main", self.root / "wt"
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q", str(main)], check=True)
        subprocess.run([*git, "-C", str(main), "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        subprocess.run([*git, "-C", str(main), "worktree", "add", "-q", str(worktree)], check=True)
        (main / ".isv").mkdir()
        (main / ".isv" / "config.toml").write_text('[review]\nexternal_cmd = "pwd"\n', encoding="utf-8")
        os.chdir(worktree)
        (worktree / "prompt.md").write_text("check this\n", encoding="utf-8")

        code, out = self._review()
        self.assertEqual(code, 0)
        self.assertEqual(Path(out.strip()).resolve(), worktree.resolve())

    def test_empty_entry_for_the_author_tool_exits_3(self) -> None:
        self._configure("cat", by_tool={"codex": ""})
        os.environ["ISV_ACTOR"] = "agent:codex/gpt-6"
        self.assertEqual(self._review()[0], 3)


if __name__ == "__main__":
    unittest.main()
