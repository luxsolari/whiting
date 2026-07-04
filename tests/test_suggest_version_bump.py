import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from suggest_version_bump import classify_bump, next_version  # noqa: E402


class TestClassifyBump(unittest.TestCase):
    def test_no_conventional_commits_is_none(self):
        self.assertEqual(classify_bump(["random commit", "wip"]), "none")

    def test_fix_only_is_patch(self):
        self.assertEqual(classify_bump(["fix: correct off-by-one"]), "patch")

    def test_feat_outranks_fix(self):
        self.assertEqual(
            classify_bump(["fix: correct off-by-one", "feat: add widget"]),
            "minor",
        )

    def test_breaking_bang_outranks_everything(self):
        self.assertEqual(
            classify_bump(["feat: add widget", "fix!: drop legacy flag"]),
            "major",
        )

    def test_breaking_change_footer_triggers_major(self):
        subjects = ["feat: add widget"]
        bodies = ["feat: add widget\n\nBREAKING CHANGE: removes old API"]
        self.assertEqual(classify_bump(subjects, bodies), "major")

    def test_non_conventional_commits_are_ignored(self):
        self.assertEqual(
            classify_bump(["Merge pull request #1", "fix: correct bug"]),
            "patch",
        )


class TestNextVersion(unittest.TestCase):
    def test_patch_bump(self):
        self.assertEqual(next_version("v1.2.3", "patch"), "v1.2.4")

    def test_minor_bump_resets_patch(self):
        self.assertEqual(next_version("v1.2.3", "minor"), "v1.3.0")

    def test_major_bump_resets_minor_and_patch(self):
        self.assertEqual(next_version("v1.2.3", "major"), "v2.0.0")

    def test_none_bump_raises(self):
        with self.assertRaises(ValueError):
            next_version("v1.2.3", "none")


if __name__ == "__main__":
    unittest.main()
