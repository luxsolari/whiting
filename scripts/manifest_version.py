#!/usr/bin/env python3
"""Print the version a package manifest declares for itself.

Only the manifest's own version counts: a `version` nested inside
`dependencies`, `packages`, or any other object is ignored.

Supports `.json` (npm's `package.json`, Claude Code's `plugin.json`) and
`.toml` (`pyproject.toml`, `[project]` or `[tool.poetry]`).

Usage:
    manifest_version.py <manifest-file>

Prints the version and exits 0; exits 1 with nothing on stdout when the
file declares no version, or can't be parsed.
"""
import json
import re
import sys
from pathlib import Path

# Fallback for Python < 3.11, which has no tomllib: match `version = "..."`
# only while inside the [project] or [tool.poetry] table.
TOML_TABLE_RE = re.compile(r"^\s*\[([^\]]+)\]")
TOML_VERSION_RE = re.compile(r"""^\s*version\s*=\s*["']([^"']+)["']""")
TOML_TABLES = ("project", "tool.poetry")


def from_json(text):
    data = json.loads(text)
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    return version if isinstance(version, str) else None


def from_toml(text):
    try:
        import tomllib
    except ModuleNotFoundError:
        return from_toml_fallback(text)
    data = tomllib.loads(text)
    candidates = (
        data.get("project", {}).get("version"),
        data.get("tool", {}).get("poetry", {}).get("version"),
    )
    for version in candidates:
        if isinstance(version, str):
            return version
    return None


def from_toml_fallback(text):
    table = None
    for line in text.splitlines():
        table_match = TOML_TABLE_RE.match(line)
        if table_match:
            table = table_match.group(1).strip()
            continue
        if table not in TOML_TABLES:
            continue
        version_match = TOML_VERSION_RE.match(line)
        if version_match:
            return version_match.group(1)
    return None


def manifest_version(path):
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".toml"):
        return from_toml(text)
    return from_json(text)


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    try:
        version = manifest_version(argv[1])
    except (OSError, ValueError):
        return 1
    if not version:
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
