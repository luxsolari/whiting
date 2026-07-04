import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from render_template import render  # noqa: E402


class TestRenderTemplate(unittest.TestCase):
    def test_substitutes_known_placeholder(self):
        self.assertEqual(render("Hello {{NAME}}!", {"NAME": "whiting"}), "Hello whiting!")

    def test_substitutes_multiple_placeholders(self):
        result = render("{{A}} and {{B}}", {"A": "one", "B": "two"})
        self.assertEqual(result, "one and two")

    def test_missing_key_raises(self):
        with self.assertRaises(KeyError):
            render("Hello {{NAME}}!", {})

    def test_no_placeholders_returns_text_unchanged(self):
        self.assertEqual(render("plain text", {}), "plain text")

    def test_cli_rejects_malformed_key_value_arg(self):
        """CLI should reject arguments without '=' and exit cleanly without traceback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "test.txt"
            template_file.write_text("Hello {{NAME}}!", encoding="utf-8")

            # Invoke the script as a subprocess with a malformed argument (no '=')
            result = subprocess.run(
                [sys.executable, "scripts/render_template.py", str(template_file), "BADARG"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
            )

            # Should exit with code 1
            self.assertEqual(result.returncode, 1)
            # Stderr should contain the usage message
            self.assertIn("Usage: render_template.py", result.stderr)
            # Should NOT contain a Python traceback or ValueError
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("ValueError", result.stderr)


if __name__ == "__main__":
    unittest.main()
