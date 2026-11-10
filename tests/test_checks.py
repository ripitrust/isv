import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from isv import checks, guard
from isv.cli import _template
from isv.config import Config, Detector

GOOD_BODY = """## Why
Charge credits per fill.

## What
Adds the ledger table.

## Verification
pytest -q: 12 passed

## Risk & rollback
Revert the PR; the migration is additive.

## Surface budget
- ledger_entries (table): no existing table records balance movements
"""


class PrBodyTest(unittest.TestCase):
    def test_complete_body_passes(self) -> None:
        self.assertEqual(checks.pr_body(GOOD_BODY, Config(root=Path("."))), [])

    def test_missing_and_empty_sections_fail(self) -> None:
        body = "## Why\nbecause\n\n## What\n\n## Verification\nran it\n"
        problems = checks.pr_body(body, Config(root=Path(".")))
        self.assertIn("empty section: ## What", problems)
        self.assertIn("missing section: ## Risk", problems)
        self.assertIn("missing section: ## Surface budget", problems)


class SurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.repo / "migrations").mkdir()
        (self.repo / "migrations" / "0001.py").write_text("op.create_table('accounts')\n")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "base")
        self._git("checkout", "-q", "-b", "feature")
        (self.repo / "migrations" / "0002.py").write_text(
            "op.create_table('ledger_entries')\nop.create_table(\"quotes\")\n"
        )
        self._git("add", ".")
        self._git("commit", "-q", "-m", "add tables")
        self.config = Config(
            root=self.repo,
            detectors=(
                Detector("table", ("migrations/*.py",), r"create_table\(\s*[\"']([A-Za-z0-9_]+)"),
            ),
            risk_paths=("migrations/**",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def test_detects_only_added_surface(self) -> None:
        found = checks.detect_surface("main", self.config, self.repo)
        self.assertEqual(sorted(f.identifier for f in found), ["ledger_entries", "quotes"])

    def test_unjustified_surface_fails(self) -> None:
        found = checks.detect_surface("main", self.config, self.repo)
        problems = checks.surface(GOOD_BODY, found)
        self.assertEqual(len(problems), 1)
        self.assertIn("quotes", problems[0])

    def test_none_with_new_surface_fails(self) -> None:
        found = checks.detect_surface("main", self.config, self.repo)
        body = GOOD_BODY.split("## Surface budget")[0] + "## Surface budget\nnone\n"
        self.assertIn("says none", checks.surface(body, found)[0])

    def test_risk_paths(self) -> None:
        self.assertEqual(checks.risk("main", self.config, self.repo), ["migrations/0002.py"])

    def test_glob_double_star_matches_top_level(self) -> None:
        self.assertTrue(checks.matches("test_x.py", ("**/test_*.py",)))
        self.assertTrue(checks.matches("a/b/test_x.py", ("**/test_*.py",)))


class GuardTest(unittest.TestCase):
    def test_blocks_force_push_and_no_verify(self) -> None:
        for command in (
            "git push --force origin main",
            "git push -f",
            "git push origin +main",
            "git push --force-with-lease",
            "git commit --no-verify -m x",
        ):
            self.assertIsNotNone(guard.check(command), command)

    def test_allows_ordinary_commands(self) -> None:
        for command in ("git push origin feature", "git commit -m 'fix -f flag'", "ls -f"):
            self.assertIsNone(guard.check(command), command)


class TemplateConfigTest(unittest.TestCase):
    def test_example_detector_parses_when_uncommented(self) -> None:
        # Users enable the example by deleting "# "; it must stay valid TOML.
        text = _template("config")
        block = text[text.index("# [[surface.detectors]]"):]
        raw = tomllib.loads(re.sub(r"(?m)^# ", "", block))
        pattern = raw["surface"]["detectors"][0]["pattern"]
        self.assertEqual(re.search(pattern, 'op.create_table("ledger",').group(1), "ledger")

    def test_project_adr_dir_loads_and_defaults_to_none(self) -> None:
        from isv import config as config_mod
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(config_mod.load(root).adr_dir, "")
            (root / ".isv").mkdir()
            (root / ".isv" / "config.toml").write_text('[project]\nadr_dir = "docs/decisions"\n')
            self.assertEqual(config_mod.load(root).adr_dir, "docs/decisions")

    def test_decision_card_asks_for_the_teachback_answer(self) -> None:
        # A card that only shows its check question lets a bare choice pass for a ruling.
        card = _template("decision-card")
        self.assertIn("**Reply with:**", card)
        self.assertLess(card.index("**Check:**"), card.index("**Reply with:**"))

    def test_example_reviewer_table_parses_when_uncommented(self) -> None:
        text = _template("config")
        block = text[text.index("# [review.external_cmd_by_tool]"):text.index("[risk]")]
        raw = tomllib.loads(re.sub(r"(?m)^# ", "", block))
        self.assertTrue(raw["review"]["external_cmd_by_tool"]["codex"].startswith("claude "))


if __name__ == "__main__":
    unittest.main()
