import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from shields_escape import shields_escape  # noqa: E402


class TestShieldsEscape(unittest.TestCase):
    def test_no_special_chars_unchanged(self):
        self.assertEqual(shields_escape("MIT"), "MIT")

    def test_single_hyphen_doubled(self):
        self.assertEqual(shields_escape("Apache-2.0"), "Apache--2.0")

    def test_multiple_hyphens_each_doubled(self):
        self.assertEqual(shields_escape("BSD-3-Clause"), "BSD--3--Clause")

    def test_underscore_doubled(self):
        self.assertEqual(shields_escape("a_b"), "a__b")

    def test_space_becomes_underscore(self):
        self.assertEqual(shields_escape("GNU GPL"), "GNU_GPL")

    def test_cli_outputs_escaped_without_trailing_newline(self):
        result = subprocess.run(
            [sys.executable, "scripts/shields_escape.py", "Apache-2.0"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Apache--2.0")


if __name__ == "__main__":
    unittest.main()
