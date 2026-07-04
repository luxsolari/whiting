import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "suggest_version_bump.py")


def run_git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True, text=True)


class TestSuggestVersionBumpCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        run_git(["init", "-q"], self.repo)
        run_git(["config", "user.email", "test@example.com"], self.repo)
        run_git(["config", "user.name", "Test"], self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message):
        run_git(["commit", "-q", "--allow-empty", "-m", message], self.repo)

    def tag(self, name):
        run_git(["tag", name], self.repo)

    def run_script(self):
        return subprocess.run(
            [sys.executable, SCRIPT], cwd=self.repo, capture_output=True, text=True,
        )

    def test_no_tags_and_a_feat_commit_suggests_v0_1_0(self):
        self.commit("feat: first feature")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Suggested next version: v0.1.0", result.stdout)

    def test_patch_bump_after_existing_tag(self):
        self.commit("feat: first feature")
        self.tag("v1.0.0")
        self.commit("fix: correct bug")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Suggested next version: v1.0.1", result.stdout)

    def test_no_relevant_commits_since_tag_exits_nonzero(self):
        self.commit("feat: first feature")
        self.tag("v1.0.0")
        self.commit("docs: fix typo")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no release needed", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
