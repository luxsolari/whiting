import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from merge_agents_md import heading_key, merge, missing_sections  # noqa: E402

TEMPLATE = """# Agent Rules

Preamble line.

## Register

Be direct.

## Work log

Append to BITACORA.md.

## No direct pushes to main

Use a PR.
"""


class TestMergeAgentsMd(unittest.TestCase):
    def test_appends_only_missing_sections(self):
        existing = "# House rules\n\n## Work log\n\nOur own log rule.\n"
        merged = merge(existing, TEMPLATE)
        self.assertIn("## Work log\n\nOur own log rule.", merged)
        self.assertEqual(merged.count("## Work log"), 1)
        self.assertNotIn("Append to BITACORA.md.", merged)
        self.assertIn("## Register", merged)
        self.assertIn("## No direct pushes to main", merged)

    def test_existing_content_is_never_rewritten(self):
        existing = "# House rules\n\nKeep this exact text.\n\n## Register\n\nOurs.\n"
        merged = merge(existing, TEMPLATE)
        self.assertTrue(merged.startswith(existing.rstrip("\n")))

    def test_template_preamble_is_not_appended(self):
        merged = merge("# House rules\n", TEMPLATE)
        self.assertNotIn("Preamble line.", merged)

    def test_branch_specific_heading_counts_as_present(self):
        existing = "## No direct pushes to develop\n\nOurs.\n"
        self.assertNotIn(
            "No direct pushes to main",
            [h for h, _ in missing_sections(existing, TEMPLATE)],
        )

    def test_heading_match_is_case_and_punctuation_insensitive(self):
        self.assertEqual(heading_key("Semver-bump discipline"), heading_key("SEMVER BUMP DISCIPLINE"))

    def test_no_missing_sections_leaves_file_untouched(self):
        merged = merge(TEMPLATE, TEMPLATE)
        self.assertEqual(merged, TEMPLATE)


if __name__ == "__main__":
    unittest.main()
