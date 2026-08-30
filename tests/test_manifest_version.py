import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from manifest_version import from_toml_fallback, manifest_version  # noqa: E402


def write(tmp, name, text):
    path = Path(tmp) / name
    path.write_text(text, encoding="utf-8")
    return path


class TestManifestVersion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_reads_top_level_json_version(self):
        path = write(self.tmp, "plugin.json", '{"name": "demo", "version": "1.2.3"}')
        self.assertEqual(manifest_version(path), "1.2.3")

    def test_ignores_a_version_nested_in_dependencies(self):
        path = write(
            self.tmp,
            "package.json",
            '{"dependencies": {"left-pad": {"version": "9.9.9"}}, "version": "1.2.3"}',
        )
        self.assertEqual(manifest_version(path), "1.2.3")

    def test_dependency_version_alone_is_not_the_manifest_version(self):
        path = write(self.tmp, "package.json", '{"dependencies": {"left-pad": "9.9.9"}}')
        self.assertIsNone(manifest_version(path))

    def test_non_string_version_is_rejected(self):
        path = write(self.tmp, "package.json", '{"version": 3}')
        self.assertIsNone(manifest_version(path))

    def test_invalid_json_raises_valueerror(self):
        path = write(self.tmp, "package.json", "{not json")
        with self.assertRaises(ValueError):
            manifest_version(path)

    def test_reads_pyproject_project_version(self):
        path = write(self.tmp, "pyproject.toml", '[project]\nname = "demo"\nversion = "1.2.3"\n')
        self.assertEqual(manifest_version(path), "1.2.3")

    def test_reads_pyproject_poetry_version(self):
        path = write(self.tmp, "pyproject.toml", '[tool.poetry]\nversion = "1.2.3"\n')
        self.assertEqual(manifest_version(path), "1.2.3")

    def test_toml_dependency_version_is_ignored(self):
        text = '[project]\nname = "demo"\n\n[tool.poetry.dependencies]\nrequests = "2.0.0"\nversion = "9.9.9"\n'
        path = write(self.tmp, "pyproject.toml", text)
        self.assertIsNone(manifest_version(path))
        self.assertIsNone(from_toml_fallback(text))

    def test_toml_fallback_matches_tomllib(self):
        text = '[build-system]\nrequires = []\n\n[project]\nversion = "4.5.6"\n'
        self.assertEqual(from_toml_fallback(text), "4.5.6")


if __name__ == "__main__":
    unittest.main()
