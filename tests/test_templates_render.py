import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from render_template import render  # noqa: E402

TEMPLATES = Path(__file__).parent.parent / "templates"


class TestTemplatesRender(unittest.TestCase):
    def test_changelog_template_needs_no_placeholders(self):
        text = (TEMPLATES / "CHANGELOG.md.tmpl").read_text()
        result = render(text, {})
        self.assertIn("## [Unreleased]", result)

    def test_readme_template_renders_with_project_fields(self):
        text = (TEMPLATES / "README.md.tmpl").read_text()
        result = render(
            text,
            {
                "PROJECT_NAME": "demo",
                "DESCRIPTION": "A demo project.",
                "REPO_SLUG": "acme/demo",
                "LICENSE_NAME": "MIT",
            },
        )
        self.assertIn("# demo", result)
        self.assertIn("A demo project.", result)
        self.assertIn("https://img.shields.io/github/v/release/acme/demo", result)
        self.assertIn("https://github.com/acme/demo/releases", result)
        self.assertIn("license-MIT-blue.svg", result)
        self.assertNotIn("{{", result)

    def test_license_template_renders_with_year_and_author(self):
        text = (TEMPLATES / "LICENSE-MIT.tmpl").read_text()
        result = render(text, {"YEAR": "2026", "AUTHOR": "Lux Solari"})
        self.assertIn("Copyright (c) 2026 Lux Solari", result)
        self.assertIn("MIT License", result)

    def test_agents_template_renders_with_default_branch(self):
        text = (TEMPLATES / "AGENTS.md.tmpl").read_text()
        result = render(text, {"DEFAULT_BRANCH": "main"})
        self.assertIn("No direct pushes to main", result)

    def test_claude_template_imports_agents(self):
        text = (TEMPLATES / "CLAUDE.md.tmpl").read_text()
        self.assertEqual(text.strip(), "@AGENTS.md")


if __name__ == "__main__":
    unittest.main()
