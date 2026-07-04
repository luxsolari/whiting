# Whiting Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `changelog-releases-assistant` to `whiting` and extend it into four focused skills — `inspect`, `repo-init`, `commit-conventions`, `semver-release` — covering repo bootstrap, Conventional Commits enforcement, semver-driven version bumps, and the existing CHANGELOG-to-GitHub-Release automation, per `docs/superpowers/specs/2026-07-04-whiting-plugin-design.md`.

**Architecture:** Pure-function core logic (commit classification, template rendering) lives in small, independently-testable Python scripts under `scripts/`; enforcement lives in tracked POSIX-sh git hooks under `scripts/hooks/` activated via `core.hooksPath`; each of the four skills is a `SKILL.md` that orchestrates these scripts/templates for the agent, never duplicating logic in prose.

**Tech Stack:** Python 3 stdlib only (no pytest, `unittest` + direct script invocation), POSIX `/bin/sh` (no bash-isms, no Node/npm), `git`, `gh` CLI.

## Global Constraints

- No new runtime dependencies: Python stdlib only, no `pip install`; hooks are POSIX `/bin/sh`, no Node/npm.
- Every installed automation file stays generic: no repo name, owner, or path hardcoded (matches the existing `extract_changelog.py`/`release.yml` convention).
- Tag scheme is assumed `v*.*.*` unless a repo's `inspect` run says otherwise — never silently hardcode a different scheme.
- Clean-break rename: no compatibility alias for `changelog-releases-assistant`.
- `inspect` never writes files — read-only, always.
- No GitHub server-side branch-protection API *writes* — only local `pre-push` enforcement. Reading branch-protection status (for `inspect`'s report) is fine.
- Hard-to-reverse, externally-visible actions (tag push, PR merge, GitHub repo rename, pushing to another repo) always get an explicit human confirmation step before they run — never automatic.

## Setup (once, before Task 1)

```bash
git checkout -b feat/whiting-rebrand
```

All tasks below commit to this branch. Task 13 pushes it, opens a PR, and merges it into `main`.

---

### Task 1: `suggest_version_bump.py` — commit classification and version arithmetic

**Files:**
- Create: `scripts/suggest_version_bump.py`
- Test: `tests/test_suggest_version_bump.py`

**Interfaces:**
- Produces: `classify_bump(commit_subjects: list[str], commit_bodies: list[str] | None = None) -> str` (returns `"major"`, `"minor"`, `"patch"`, or `"none"`); `next_version(current: str, bump: str) -> str` (raises `ValueError` if `bump == "none"`). Both consumed by Task 2's `main()`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_suggest_version_bump.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_suggest_version_bump.py`
Expected: `ModuleNotFoundError: No module named 'suggest_version_bump'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Suggest the next semver bump from Conventional Commits since the last tag."""
import re

COMMIT_TYPE_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$"
)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)


def classify_bump(commit_subjects, commit_bodies=None):
    """Classify the required semver bump from commit subject lines.

    commit_bodies, if given, is a list of full commit message bodies
    aligned with commit_subjects, checked for a 'BREAKING CHANGE:' footer.
    """
    bodies = commit_bodies or [""] * len(commit_subjects)
    level = "none"
    for subject, body in zip(commit_subjects, bodies):
        match = COMMIT_TYPE_RE.match(subject)
        if not match:
            continue
        if match.group("breaking") or BREAKING_FOOTER_RE.search(body):
            return "major"
        commit_type = match.group("type")
        if commit_type == "feat" and level != "major":
            level = "minor"
        elif commit_type == "fix" and level not in ("major", "minor"):
            level = "patch"
    return level


def next_version(current, bump):
    """Compute the next version string from a 'vX.Y.Z' tag and a bump level."""
    major, minor, patch = (int(part) for part in current.lstrip("v").split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    if bump == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    raise ValueError(f"No release needed: bump={bump!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_suggest_version_bump.py`
Expected: `OK` (10 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/suggest_version_bump.py tests/test_suggest_version_bump.py
git commit -m "feat: add commit classification and version arithmetic for semver bumps"
```

---

### Task 2: `suggest_version_bump.py` — CLI (last tag, commits since, report)

**Files:**
- Modify: `scripts/suggest_version_bump.py`
- Test: `tests/test_suggest_version_bump_cli.py`

**Interfaces:**
- Consumes: `classify_bump`, `next_version` from Task 1 (same file).
- Produces: CLI entry point `python3 scripts/suggest_version_bump.py`, exit code `0` with a suggestion printed, or `1` with "no release needed"/"nothing to release" printed. This is the exact invocation `semver-release`'s `SKILL.md` (Task 11) tells the agent to run.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_suggest_version_bump_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/test_suggest_version_bump_cli.py`
Expected: FAIL — script exits with an error / produces no stdout (no `main()` yet).

- [ ] **Step 3: Extend the implementation**

Append to `scripts/suggest_version_bump.py`:

```python
import subprocess
import sys


def last_tag():
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v*.*.*"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def commits_since(tag):
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    subjects = subprocess.run(
        ["git", "log", rev_range, "--format=%s"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    bodies = subprocess.run(
        ["git", "log", rev_range, "--format=%B%x00"],
        capture_output=True, text=True, check=True,
    ).stdout.split("\x00")
    return subjects, bodies


def main():
    tag = last_tag()
    subjects, bodies = commits_since(tag)
    if not subjects:
        print(f"No commits since {tag or '(no tags yet)'} — nothing to release.")
        return 1
    bump = classify_bump(subjects, bodies)
    if bump == "none":
        print(f"No feat/fix/breaking commits since {tag or '(no tags yet)'} — no release needed.")
        return 1
    baseline = tag or "v0.0.0"
    suggested = next_version(baseline, bump)
    print(f"Last tag: {tag or '(none)'}")
    print(f"Commits considered: {len(subjects)}")
    print(f"Bump level: {bump}")
    print(f"Suggested next version: {suggested}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Move the existing `import re` to the top of the file alongside the new `import subprocess` and `import sys` (all three imports at the top, in that order).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/test_suggest_version_bump_cli.py`
Expected: `OK` (3 tests)

Also re-run Task 1's test to confirm no regression: `python3 tests/test_suggest_version_bump.py` → `OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/suggest_version_bump.py tests/test_suggest_version_bump_cli.py
git commit -m "feat: add CLI to suggest_version_bump.py (last tag, commits since, report)"
```

---

### Task 3: `render_template.py` — generic placeholder substitution

**Files:**
- Create: `scripts/render_template.py`
- Test: `tests/test_render_template.py`

**Interfaces:**
- Produces: `render(template_text: str, mapping: dict[str, str]) -> str` (raises `KeyError` on an unmapped `{{KEY}}`); CLI `python3 scripts/render_template.py <template-file> [KEY=VALUE ...]` printing the rendered result to stdout. Consumed by `repo-init` (Task 9) and `commit-conventions` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_template.py
import sys
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/test_render_template.py`
Expected: `ModuleNotFoundError: No module named 'render_template'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Render a template by substituting {{KEY}} placeholders."""
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def render(template_text, mapping):
    def replace(match):
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"Missing template value for {{{{{key}}}}}")
        return mapping[key]

    return PLACEHOLDER_RE.sub(replace, template_text)


def main():
    if len(sys.argv) < 2:
        print("Usage: render_template.py <template-file> [KEY=VALUE ...]", file=sys.stderr)
        return 1
    template_path = Path(sys.argv[1])
    mapping = dict(arg.split("=", 1) for arg in sys.argv[2:])
    print(render(template_path.read_text(encoding="utf-8"), mapping), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/test_render_template.py`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/render_template.py tests/test_render_template.py
git commit -m "feat: add render_template.py for generic {{KEY}} substitution"
```

---

### Task 4: `commit-msg` hook — Conventional Commits enforcement

**Files:**
- Create: `scripts/hooks/commit-msg`
- Test: `tests/test_commit_msg_hook.sh`

**Interfaces:**
- Produces: executable `scripts/hooks/commit-msg`, invoked by git as `commit-msg <path-to-commit-message-file>`. Referenced by `commit-conventions`'s `SKILL.md` (Task 10) and activated repo-wide in Task 13.

- [ ] **Step 1: Write the hook**

```sh
#!/bin/sh
# Rejects commit messages that don't follow Conventional Commits.
set -eu

commit_msg_file="$1"
subject=$(head -n 1 "$commit_msg_file")

case "$subject" in
    Merge\ *) exit 0 ;;
esac

pattern='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+'

if ! printf '%s' "$subject" | grep -qE "$pattern"; then
    echo "commit-msg: rejected — subject line must follow Conventional Commits:" >&2
    echo "  type(scope)?: description" >&2
    echo "  allowed types: feat fix docs style refactor perf test build ci chore revert" >&2
    echo "  example: feat(api): add pagination to /users endpoint" >&2
    echo "got: $subject" >&2
    exit 1
fi
```

```bash
mkdir -p scripts/hooks
chmod +x scripts/hooks/commit-msg
```

- [ ] **Step 2: Write the test script**

```sh
#!/bin/sh
set -eu

hook="$(cd "$(dirname "$0")/.." && pwd)/scripts/hooks/commit-msg"
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

fail=0

assert_pass() {
    printf '%s\n' "$1" > "$tmp"
    if ! "$hook" "$tmp" >/dev/null 2>&1; then
        echo "FAIL (expected pass): $1"
        fail=1
    fi
}

assert_fail() {
    printf '%s\n' "$1" > "$tmp"
    if "$hook" "$tmp" >/dev/null 2>&1; then
        echo "FAIL (expected reject): $1"
        fail=1
    fi
}

assert_pass "feat(api): add pagination to /users endpoint"
assert_pass "fix: correct off-by-one in paginator"
assert_pass "chore!: drop support for node 16"
assert_pass "Merge branch 'main' into feature"

assert_fail "added pagination"
assert_fail "Feat: wrong case"
assert_fail "fix:missing space"

if [ "$fail" -eq 0 ]; then
    echo "All commit-msg hook tests passed."
else
    exit 1
fi
```

```bash
chmod +x tests/test_commit_msg_hook.sh
```

- [ ] **Step 3: Run the test**

Run: `sh tests/test_commit_msg_hook.sh`
Expected: `All commit-msg hook tests passed.`

- [ ] **Step 4: Commit**

```bash
git add scripts/hooks/commit-msg tests/test_commit_msg_hook.sh
git commit -m "feat: add commit-msg hook enforcing Conventional Commits"
```

---

### Task 5: `pre-push` hook — block direct pushes to the default branch

**Files:**
- Create: `scripts/hooks/pre-push`
- Test: `tests/test_pre_push_hook.sh`

**Interfaces:**
- Produces: executable `scripts/hooks/pre-push`, invoked by git as `pre-push <remote-name> <remote-url>` with ref lines on stdin. Reads the `whiting.defaultbranch` git-config value (falls back to `main`). Referenced by `commit-conventions`'s `SKILL.md` (Task 10), which is responsible for setting `whiting.defaultbranch`.

- [ ] **Step 1: Write the hook**

```sh
#!/bin/sh
# Blocks direct pushes to the repo's protected (default) branch.
# Tags and other branches are unaffected — only a push whose remote ref IS
# the protected branch is rejected; land changes via PR/merge instead.
set -eu

protected_branch=$(git config --get whiting.defaultbranch || true)
protected_branch=${protected_branch:-main}

while read -r local_ref local_sha remote_ref remote_sha; do
    case "$remote_ref" in
        "refs/heads/$protected_branch")
            echo "pre-push: rejected — direct pushes to '$protected_branch' aren't allowed." >&2
            echo "pre-push: push a branch and open a PR instead." >&2
            exit 1
            ;;
    esac
done

exit 0
```

```bash
chmod +x scripts/hooks/pre-push
```

- [ ] **Step 2: Write the test script**

```sh
#!/bin/sh
set -eu

hook="$(cd "$(dirname "$0")/.." && pwd)/scripts/hooks/pre-push"
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

cd "$workdir"
git init -q

fail=0

assert_blocked() {
    git config whiting.defaultbranch "$1"
    if printf '%s\n' "$2" | "$hook" origin git@example.com:test.git >/dev/null 2>&1; then
        echo "FAIL (expected block): $2"
        fail=1
    fi
}

assert_allowed() {
    git config whiting.defaultbranch "$1"
    if ! printf '%s\n' "$2" | "$hook" origin git@example.com:test.git >/dev/null 2>&1; then
        echo "FAIL (expected allow): $2"
        fail=1
    fi
}

assert_blocked main "refs/heads/main abc123 refs/heads/main def456"
assert_allowed main "refs/heads/feature abc123 refs/heads/feature def456"
assert_allowed main "HEAD abc123 refs/tags/v1.0.0 def456"
assert_blocked trunk "refs/heads/trunk abc123 refs/heads/trunk def456"

if [ "$fail" -eq 0 ]; then
    echo "All pre-push hook tests passed."
else
    exit 1
fi
```

```bash
chmod +x tests/test_pre_push_hook.sh
```

- [ ] **Step 3: Run the test**

Run: `sh tests/test_pre_push_hook.sh`
Expected: `All pre-push hook tests passed.`

- [ ] **Step 4: Commit**

```bash
git add scripts/hooks/pre-push tests/test_pre_push_hook.sh
git commit -m "feat: add pre-push hook blocking direct pushes to the default branch"
```

---

### Task 6: Bundled templates + rendering smoke test

**Files:**
- Create: `templates/CHANGELOG.md.tmpl`
- Create: `templates/README.md.tmpl`
- Create: `templates/LICENSE-MIT.tmpl`
- Create: `templates/AGENTS.md.tmpl`
- Create: `templates/CLAUDE.md.tmpl`
- Test: `tests/test_templates_render.py`

**Interfaces:**
- Consumes: `render()` from Task 3.
- Produces: the five template files at these exact paths, referenced by `repo-init`'s `SKILL.md` (Task 9) and `commit-conventions`'s `SKILL.md` (Task 10). Placeholder contract: `README.md.tmpl` needs `PROJECT_NAME`, `DESCRIPTION`; `LICENSE-MIT.tmpl` needs `YEAR`, `AUTHOR`; `AGENTS.md.tmpl` needs `DEFAULT_BRANCH`; `CHANGELOG.md.tmpl` and `CLAUDE.md.tmpl` need no placeholders.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_templates_render.py
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
        result = render(text, {"PROJECT_NAME": "demo", "DESCRIPTION": "A demo project."})
        self.assertIn("# demo", result)
        self.assertIn("A demo project.", result)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/test_templates_render.py`
Expected: `FileNotFoundError` (templates don't exist yet)

- [ ] **Step 3: Write the templates**

```markdown
<!-- templates/CHANGELOG.md.tmpl -->
# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

```markdown
<!-- templates/README.md.tmpl -->
# {{PROJECT_NAME}}

{{DESCRIPTION}}

## Install

<!-- Add install instructions here. -->

## Usage

<!-- Add usage instructions here. -->

## License

MIT — see [LICENSE](LICENSE).
```

```text
<!-- templates/LICENSE-MIT.tmpl -->
MIT License

Copyright (c) {{YEAR}} {{AUTHOR}}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

```markdown
<!-- templates/AGENTS.md.tmpl -->
# Agent Rules

This repo uses [whiting](https://github.com/luxsolari/whiting) for release
discipline. The following rules apply to human contributors and AI agents
alike.

## Conventional Commits

Every commit subject line must follow:

```
type(scope)!: description
```

Allowed types: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build`
`ci` `chore` `revert`. `scope` is optional. A `!` before the colon, or a
`BREAKING CHANGE:` footer in the body, marks a breaking change.

This is enforced locally by a `commit-msg` hook. After cloning, activate it
once with:

```
git config core.hooksPath scripts/hooks
```

## Semver-bump discipline

Version numbers are never hand-edited. The next version is derived from
commits since the last tag via `scripts/suggest_version_bump.py` (`feat` →
minor, `fix` → patch, breaking → major). Git tags are the source of truth
for "what version is this."

## Changelog-first workflow

Every user-facing change adds an entry under `## [Unreleased]` in
`CHANGELOG.md`, in the same commit or PR that makes the change. No
undocumented changes.

## No direct pushes to {{DEFAULT_BRANCH}}

Land changes via a branch and a pull request. Direct pushes to
`{{DEFAULT_BRANCH}}` are blocked locally by a `pre-push` hook.
```

```text
<!-- templates/CLAUDE.md.tmpl -->
@AGENTS.md
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/test_templates_render.py`
Expected: `OK` (5 tests)

- [ ] **Step 5: Commit**

```bash
git add templates/
git commit -m "feat: add repo-init and commit-conventions templates"
```

---

### Task 7: `inspect_repo.sh` auditor + test runner aggregator

**Files:**
- Create: `scripts/inspect_repo.sh`
- Create: `scripts/run_tests.sh`
- Test: `tests/test_inspect_repo.sh`

**Interfaces:**
- Produces: executable `scripts/inspect_repo.sh` (run from the repo root being audited, no arguments, exits `0` unless the target isn't a git repo), and `scripts/run_tests.sh` (runs every `tests/test_*.py` and `tests/test_*.sh`, exit code `0` iff all pass). Referenced by `inspect`'s `SKILL.md` (Task 8).

- [ ] **Step 1: Write the auditor script**

```sh
#!/bin/sh
# Audits a repo against whiting's conventions. Read-only, makes no changes.
set -u

pass=0
warn=0
fail=0

report_ok() { printf '✅ %s\n' "$1"; pass=$((pass + 1)); }
report_warn() { printf '⚠️  %s\n' "$1"; warn=$((warn + 1)); }
report_fail() { printf '❌ %s\n' "$1"; fail=$((fail + 1)); }

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    report_ok "git repository present"
else
    report_fail "not a git repository"
    printf '\n%d ok, %d warnings, %d failed\n' "$pass" "$warn" "$fail"
    exit 1
fi

default_branch=$(git config --get whiting.defaultbranch || true)
if [ -z "$default_branch" ]; then
    default_branch=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)
fi
default_branch=${default_branch:-main}
report_ok "default branch resolved as '$default_branch'"

[ -f LICENSE ] && report_ok "LICENSE present" || report_warn "LICENSE missing"
[ -f README.md ] && report_ok "README.md present" || report_warn "README.md missing"

if [ -f CHANGELOG.md ]; then
    if grep -qE '^## \[[^]]+\]' CHANGELOG.md; then
        report_ok "CHANGELOG.md present and Keep a Changelog-formatted"
    else
        report_warn "CHANGELOG.md present but no '## [X.Y.Z]' section found"
    fi
else
    report_warn "CHANGELOG.md missing"
fi

tag_sample=$(git tag -l | head -n 5)
if [ -z "$tag_sample" ]; then
    report_warn "no git tags found"
elif printf '%s\n' "$tag_sample" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    report_ok "tags follow v*.*.* scheme"
else
    report_warn "tags exist but don't match v*.*.* (found: $(printf '%s' "$tag_sample" | head -n1))"
fi

if [ -d .github/workflows ] && grep -rl -E 'gh release|softprops/action-gh-release|actions/create-release' .github/workflows 2>/dev/null | grep -q .; then
    report_warn "existing release-publishing workflow found — check before adding another"
else
    report_ok "no competing release-publishing workflow found"
fi

hooks_path=$(git config --get core.hooksPath || true)
if [ "$hooks_path" = "scripts/hooks" ]; then
    report_ok "core.hooksPath set to scripts/hooks"
else
    report_warn "core.hooksPath not set to scripts/hooks (commit-msg/pre-push hooks inactive)"
fi

recent_subjects=$(git log -20 --format=%s 2>/dev/null || true)
if [ -n "$recent_subjects" ]; then
    total=$(printf '%s\n' "$recent_subjects" | wc -l | tr -d ' ')
    conventional=$(printf '%s\n' "$recent_subjects" | grep -cE '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+' || true)
    report_ok "commit style: $conventional/$total of last $total commits already follow Conventional Commits"
else
    report_warn "no commit history to sample"
fi

if [ -f AGENTS.md ]; then
    if [ -f CLAUDE.md ] && grep -q '@AGENTS.md' CLAUDE.md; then
        report_ok "AGENTS.md present and CLAUDE.md imports it"
    else
        report_warn "AGENTS.md present but CLAUDE.md doesn't import it"
    fi
else
    report_warn "AGENTS.md missing"
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    origin_url=$(git config --get remote.origin.url || true)
    repo_slug=$(printf '%s' "$origin_url" | sed -E 's#.*[:/]([^/]+/[^/]+)(\.git)?$#\1#')
    if [ -n "$repo_slug" ] && gh api "repos/$repo_slug/branches/$default_branch/protection" >/dev/null 2>&1; then
        report_ok "GitHub branch protection enabled on '$default_branch'"
    else
        report_warn "GitHub branch protection not detected on '$default_branch' (or gh lacks admin read access)"
    fi
else
    report_warn "gh not authenticated — skipped branch protection check"
fi

printf '\n%d ok, %d warnings, %d failed\n' "$pass" "$warn" "$fail"
[ "$fail" -eq 0 ]
```

```bash
chmod +x scripts/inspect_repo.sh
```

- [ ] **Step 2: Write the test runner aggregator**

```sh
#!/bin/sh
# Runs every test in tests/: python unittest files and POSIX shell test scripts.
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

for test_file in "$root"/tests/test_*.py; do
    [ -e "$test_file" ] || continue
    echo "== $test_file =="
    python3 "$test_file" || fail=1
done

for test_file in "$root"/tests/test_*.sh; do
    [ -e "$test_file" ] || continue
    echo "== $test_file =="
    sh "$test_file" || fail=1
done

if [ "$fail" -eq 0 ]; then
    echo "All tests passed."
else
    echo "Some tests failed." >&2
fi
exit "$fail"
```

```bash
chmod +x scripts/run_tests.sh
```

- [ ] **Step 3: Write the test for inspect_repo.sh**

```sh
#!/bin/sh
set -eu

script="$(cd "$(dirname "$0")/.." && pwd)/scripts/inspect_repo.sh"
fail=0

# Case 1: not a git repo at all
workdir=$(mktemp -d)
out=$(cd "$workdir" && "$script" 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: expected exit 1 for non-git directory"; fail=1; }
printf '%s\n' "$out" | grep -q "not a git repository" || { echo "FAIL: missing 'not a git repository' message"; fail=1; }
rm -rf "$workdir"

# Case 2: minimal repo, no LICENSE/README/CHANGELOG
workdir=$(mktemp -d)
(cd "$workdir" && git init -q && git config user.email t@example.com && git config user.name Test && git commit -q --allow-empty -m "chore: init")
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "LICENSE missing" || { echo "FAIL: expected LICENSE missing warning"; fail=1; }
printf '%s\n' "$out" | grep -q "CHANGELOG.md missing" || { echo "FAIL: expected CHANGELOG.md missing warning"; fail=1; }
rm -rf "$workdir"

# Case 3: fully compliant repo
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    touch LICENSE README.md
    printf '# Changelog\n\n## [0.1.0] - 2026-01-01\n' > CHANGELOG.md
    mkdir -p scripts/hooks
    git config whiting.defaultbranch main
    git config core.hooksPath scripts/hooks
    git add -A
    git commit -q -m "feat: initial commit"
    git tag v0.1.0
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "LICENSE present" || { echo "FAIL: expected LICENSE present"; fail=1; }
printf '%s\n' "$out" | grep -q "CHANGELOG.md present and Keep a Changelog-formatted" || { echo "FAIL: expected CHANGELOG ok"; fail=1; }
printf '%s\n' "$out" | grep -q 'tags follow v\*\.\*\.\* scheme' || { echo "FAIL: expected tag scheme ok"; fail=1; }
printf '%s\n' "$out" | grep -q "core.hooksPath set to scripts/hooks" || { echo "FAIL: expected hooksPath ok"; fail=1; }
rm -rf "$workdir"

if [ "$fail" -eq 0 ]; then
    echo "All inspect_repo.sh tests passed."
else
    exit 1
fi
```

```bash
chmod +x tests/test_inspect_repo.sh
```

- [ ] **Step 4: Run the tests**

Run: `sh tests/test_inspect_repo.sh`
Expected: `All inspect_repo.sh tests passed.`

Then run the full aggregator to confirm everything built so far still passes:

Run: `sh scripts/run_tests.sh`
Expected: `All tests passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/inspect_repo.sh scripts/run_tests.sh tests/test_inspect_repo.sh
git commit -m "feat: add inspect_repo.sh auditor and run_tests.sh aggregator"
```

---

### Task 8: `skills/inspect/SKILL.md`

**Files:**
- Create: `skills/inspect/SKILL.md`

**Interfaces:**
- Consumes: `scripts/inspect_repo.sh` (Task 7).
- Produces: nothing programmatic — this is the agent-facing doc for the `inspect` skill.

- [ ] **Step 1: Write the skill doc**

```markdown
---
name: inspect
description: >-
  Audit an existing repo against whiting's conventions (Keep a Changelog,
  Conventional Commits, semver tags, GitHub Release automation, AGENTS.md/
  CLAUDE.md) and produce a compliance report plus a remediation plan. Use
  when the user wants to know what's missing or non-conforming before
  running repo-init, commit-conventions, or semver-release on a repo that
  wasn't bootstrapped by whiting from scratch. Read-only — makes no changes.
license: MIT
---

# inspect

Gives a one-shot picture of how far an existing repo is from whiting's
conventions, so you know which of `repo-init`, `commit-conventions`, and
`semver-release` to run — and with what adjustments — instead of guessing.

## When to use this skill

- "What's missing before we can wire up releases here?"
- "Adapt our existing conventions to whiting."
- "Is this repo ready for whiting's commit hooks?"
- Any repo where `repo-init` wasn't the first thing ever run in it.

## What it does

Run the bundled auditor from the repo root being inspected:

```
$CLAUDE_PLUGIN_ROOT/scripts/inspect_repo.sh
```

It checks, read-only:

- Git repo present, and the resolved default branch.
- `LICENSE`, `README.md`, `CHANGELOG.md` presence and format.
- Tag scheme (`v*.*.*` or otherwise).
- Existing release-publishing automation (to avoid recommending a
  competing workflow).
- Whether `core.hooksPath` is already wired to `scripts/hooks`.
- What fraction of the last 20 commits already follow Conventional
  Commits (tells you how disruptive turning on the `commit-msg` hook
  will be).
- Whether `AGENTS.md` exists and `CLAUDE.md` imports it.
- GitHub branch protection on the default branch (best-effort; skipped
  if `gh` isn't authenticated).

Each line is marked ✅ (compliant), ⚠️ (missing/adjustable), or ❌
(blocking problem — currently only "not a git repository").

## After running it

Turn the ⚠️/❌ lines into a remediation plan naming the specific skill to
run next:

- Missing `LICENSE`/`README.md`/`CHANGELOG.md` → run `repo-init`.
- `core.hooksPath` not set, or commits not yet following Conventional
  Commits → run `commit-conventions`; if the tag scheme isn't `v*.*.*`,
  say so explicitly so the hook regex and `semver-release`'s tag glob get
  adjusted together, not just one of them.
- No release-publishing automation and tags already exist → run
  `semver-release`, noting how many existing tags have no GitHub Release
  yet (candidates for backfill via `workflow_dispatch`).

## Scope notes

- This skill never writes files. It only reads and reports — all changes
  happen when you subsequently invoke `repo-init`, `commit-conventions`,
  or `semver-release`.
- If it reports an existing competing release-publishing workflow, tell
  the user and stop — don't invoke `semver-release` to add a second one.
```

- [ ] **Step 2: Verify by running it against this repo**

Run: `bash skills/inspect/../../scripts/inspect_repo.sh` (equivalently, `bash scripts/inspect_repo.sh` from the repo root)
Expected: prints the ✅/⚠️ report; at this point in the plan `AGENTS.md`/`CLAUDE.md` and `core.hooksPath` are still ⚠️ (Task 13 fixes that) — confirms the script gives an accurate, non-crashing report on a real, non-trivial repo.

- [ ] **Step 3: Commit**

```bash
git add skills/inspect/SKILL.md
git commit -m "docs: add inspect skill"
```

---

### Task 9: `skills/repo-init/SKILL.md`

**Files:**
- Create: `skills/repo-init/SKILL.md`

**Interfaces:**
- Consumes: `scripts/render_template.py` (Task 3), `templates/CHANGELOG.md.tmpl`, `templates/README.md.tmpl`, `templates/LICENSE-MIT.tmpl` (Task 6).
- Produces: nothing programmatic — agent-facing doc.

- [ ] **Step 1: Write the skill doc**

```markdown
---
name: repo-init
description: >-
  Bootstrap a repo's baseline — git init if needed, LICENSE, README.md
  skeleton, and a Keep a Changelog-formatted CHANGELOG.md — whether
  starting from an empty directory or filling gaps in an existing repo.
  Use when the user wants to start a new project properly or is missing
  one of these files. Never overwrites an existing file without asking.
license: MIT
---

# repo-init

Bootstraps the baseline every other whiting skill assumes is there: a git
repo, a LICENSE, a README, and a Keep a Changelog `CHANGELOG.md`.

## When to use this skill

- "Set up a new repo for this project."
- "Bootstrap this directory properly."
- "We're missing a LICENSE/CHANGELOG, can you add one?"

## Before touching anything

1. Run `git rev-parse --is-inside-work-tree`. If it fails, this is a
   from-scratch bootstrap — run `git init` before anything else.
2. Check for existing `LICENSE`, `README.md`, `CHANGELOG.md`. For each one
   that already exists, report it and ask before touching it — never
   overwrite silently. Skip files the user says to leave alone.

## What to install

Render each missing file from `$CLAUDE_PLUGIN_ROOT/templates/` using the
bundled renderer:

```
python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
  $CLAUDE_PLUGIN_ROOT/templates/CHANGELOG.md.tmpl > CHANGELOG.md
```

| Missing file | Template | Placeholders |
| --- | --- | --- |
| `CHANGELOG.md` | `templates/CHANGELOG.md.tmpl` | none |
| `README.md` | `templates/README.md.tmpl` | `PROJECT_NAME`, `DESCRIPTION` |
| `LICENSE` (MIT) | `templates/LICENSE-MIT.tmpl` | `YEAR`, `AUTHOR` |

For `README.md`, ask the user for the project name and a one-line
description before rendering:

```
python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
  $CLAUDE_PLUGIN_ROOT/templates/README.md.tmpl \
  PROJECT_NAME="my-project" DESCRIPTION="What it does, one line." > README.md
```

For `LICENSE`, ask which license (default MIT). If MIT, render
`LICENSE-MIT.tmpl` with the current year and the user's name. For any
other license, fetch the canonical text instead of guessing:
`gh api "licenses/<spdx-id>" --jq .body > LICENSE` (e.g. `apache-2.0`,
`gpl-3.0`).

## Land the change

If this is a from-scratch bootstrap, this is the first commit:
`git add -A && git commit -m "chore: initial commit"` — a valid
Conventional Commits subject even before the `commit-conventions` hook
exists to enforce it.

If retrofitting an existing, non-empty repo, land these files the same
way any other change lands there: branch, commit, PR — don't push
straight to the default branch.

## Next steps

After this, run `commit-conventions` to install the commit-message hook
and generate `AGENTS.md`/`CLAUDE.md`, then `semver-release` to wire up
release automation. `inspect` can tell you if either is already partially
in place.
```

- [ ] **Step 2: Commit**

```bash
git add skills/repo-init/SKILL.md
git commit -m "docs: add repo-init skill"
```

---

### Task 10: `skills/commit-conventions/SKILL.md`

**Files:**
- Create: `skills/commit-conventions/SKILL.md`

**Interfaces:**
- Consumes: `scripts/hooks/commit-msg`, `scripts/hooks/pre-push` (Tasks 4–5), `scripts/render_template.py` (Task 3), `templates/AGENTS.md.tmpl`, `templates/CLAUDE.md.tmpl` (Task 6).
- Produces: nothing programmatic — agent-facing doc. Documents the `whiting.defaultbranch` and `core.hooksPath` git-config convention that Task 13's dogfooding step and any target repo must set.

- [ ] **Step 1: Write the skill doc**

```markdown
---
name: commit-conventions
description: >-
  Install Conventional Commits enforcement (a commit-msg hook) and a
  no-direct-push-to-main guard (a pre-push hook), plus generate AGENTS.md
  and CLAUDE.md rule files covering commit format, semver-bump discipline,
  changelog-first workflow, and branch protection policy. Use when the
  user wants commit conventions enforced or wants Claude/agents to follow
  a documented rule set in this repo.
license: MIT
---

# commit-conventions

Installs local git hooks that enforce Conventional Commits and block
direct pushes to the default branch, and generates the `AGENTS.md` /
`CLAUDE.md` files that document these rules (and others) for both human
contributors and AI agents working in the repo.

## When to use this skill

- "Enforce conventional commits here."
- "Set up rules for how Claude should work in this repo."
- "Stop people (and agents) from pushing straight to main."

## Before touching anything

- Check `git config --get core.hooksPath`. If it's already set to
  something other than `scripts/hooks`, stop and ask before overriding —
  another tool may own it.
- Check for an existing `AGENTS.md`/`CLAUDE.md`. Never overwrite existing
  content — append/prepend instead (see below).

## What to install

1. Copy the hook scripts, unmodified, and make them executable:

   | Source (`$CLAUDE_PLUGIN_ROOT/...`) | Destination |
   | --- | --- |
   | `scripts/hooks/commit-msg` | `scripts/hooks/commit-msg` |
   | `scripts/hooks/pre-push` | `scripts/hooks/pre-push` |

   ```
   chmod +x scripts/hooks/commit-msg scripts/hooks/pre-push
   ```

2. Resolve and record the default branch once, so `pre-push` never needs
   a network call at push time:

   ```
   git config whiting.defaultbranch "$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)"
   ```

   Fall back to `main` if `gh` isn't available or the repo has no remote
   yet.

3. Activate both hooks for this clone:

   ```
   git config core.hooksPath scripts/hooks
   ```

   Note in `AGENTS.md` (below) that every other clone/contributor needs
   to run this same command once after cloning — `core.hooksPath` is a
   local, unversioned config, not something git syncs automatically.

4. Render `AGENTS.md` from `$CLAUDE_PLUGIN_ROOT/templates/AGENTS.md.tmpl`,
   substituting the resolved default branch:

   ```
   python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
     $CLAUDE_PLUGIN_ROOT/templates/AGENTS.md.tmpl \
     DEFAULT_BRANCH="main" > AGENTS.md
   ```

   If `AGENTS.md` already exists, don't overwrite it — show the user the
   template content and ask whether to append the missing rule sections.

5. Wire up `CLAUDE.md`:
   - If it doesn't exist: copy `templates/CLAUDE.md.tmpl` verbatim (it's
     just `@AGENTS.md`).
   - If it exists and doesn't already reference `AGENTS.md`: prepend the
     `@AGENTS.md` line, leaving the rest of the file untouched.

## The four rules AGENTS.md documents

- **Conventional Commits**: `type(scope)!: description`, allowed types
  `feat fix docs style refactor perf test build ci chore revert`, a
  `BREAKING CHANGE:` footer or `!` marks a breaking change.
- **Semver-bump discipline**: version numbers are derived from commits via
  `semver-release`'s bump script, never hand-edited; tags are the source
  of truth for "what version is this."
- **Changelog-first workflow**: every user-facing change adds an entry
  under `## [Unreleased]` in `CHANGELOG.md` in the same commit/PR.
- **No direct pushes to the default branch**: land changes via a branch +
  PR; the `pre-push` hook enforces this locally.

## Land the change

Branch, commit, PR — same rule the files themselves are about to start
enforcing.

## Next steps

Run `semver-release` next to wire up the version-bump-to-release pipeline
that `AGENTS.md`'s semver rule refers to.
```

- [ ] **Step 2: Commit**

```bash
git add skills/commit-conventions/SKILL.md
git commit -m "docs: add commit-conventions skill"
```

---

### Task 11: `skills/semver-release/SKILL.md` (rename + extend `changelog-releases-assistant`)

**Files:**
- Create: `skills/semver-release/SKILL.md`
- Delete: `skills/changelog-releases-assistant/SKILL.md` (and the now-empty `skills/changelog-releases-assistant/` directory)

**Interfaces:**
- Consumes: `scripts/extract_changelog.py` (unchanged, existing), `scripts/suggest_version_bump.py` (Tasks 1–2), `.github/workflows/release.yml` (unchanged, existing).
- Produces: nothing programmatic — agent-facing doc.

- [ ] **Step 1: Move and rewrite the skill doc**

```bash
mkdir -p skills/semver-release
git rm skills/changelog-releases-assistant/SKILL.md
rmdir skills/changelog-releases-assistant
```

```markdown
---
name: semver-release
description: >-
  Wire a repo's CHANGELOG.md up to its GitHub Releases, and suggest the
  next semver bump from Conventional Commits since the last tag. Use when
  the user wants to populate an empty GitHub Releases tab, backfill
  releases for existing tags, automate publishing a Release on every
  version tag push, or figure out what the next version number should be.
  Applies to any repo following Keep a Changelog conventions and tagging
  releases with a "v*.*.*" scheme.
license: MIT
---

# semver-release

Wires a repo's `CHANGELOG.md` up to its GitHub Releases: pushing a version
tag publishes a Release whose body is that version's changelog section,
verbatim. Also suggests the next version number from Conventional Commits
since the last tag, so version bumps aren't guessed by hand.

## When to use this skill

- "Populate the GitHub Releases tab for this repo."
- "Set up automatic releases from the changelog."
- "Backfill GitHub releases for our existing tags."
- "What should the next version be?" / "Cut a release."

## Before touching anything

1. **Check for an existing release workflow.** Grep `.github/workflows/*.yml`
   for `gh release`, `softprops/action-gh-release`, `actions/create-release`,
   or similar. If one exists, stop and tell the user what's already there
   instead of adding a second, competing workflow.
2. **Check `CHANGELOG.md` follows Keep a Changelog conventions**: version
   sections headed `## [X.Y.Z] — YYYY-MM-DD` (a regex on `^## \[VERSION\]`
   must match). If there's no changelog, or its format doesn't match, this
   skill needs `repo-init` run first — don't guess a format.
3. **Check the tag scheme**: `git tag -l` should show tags like `v0.1.0`.
   If tags use a different prefix or omit `v`, this skill's workflow's
   `on.push.tags` glob, `scripts/extract_changelog.py`, and
   `scripts/suggest_version_bump.py`'s `v`-prefix handling all need the
   same adjustment — don't fix one and silently leave the others broken.

## Installing release automation

Copy these files, unmodified unless step 3 above required a tag-scheme
tweak — applied consistently across all three:

| Source (`$CLAUDE_PLUGIN_ROOT/...`) | Destination |
| --- | --- |
| `scripts/extract_changelog.py` | `scripts/extract_changelog.py` |
| `scripts/suggest_version_bump.py` | `scripts/suggest_version_bump.py` |
| `.github/workflows/release.yml` | `.github/workflows/release.yml` |

`extract_changelog.py` takes a version (`v0.7.3` or `0.7.3`) and prints
the matching `## [X.Y.Z]` section of `CHANGELOG.md`, stripping the
trailing `[X.Y.Z]: https://...` reference link and any `---` separator.
The workflow runs on every `v*.*.*` tag push (and via `workflow_dispatch`
with a `tag` input for backfilling), pipes that script's output into
`gh release create` (or `gh release edit` if a release for that tag
already exists), and needs no secrets beyond the default `GITHUB_TOKEN`
(`permissions: contents: write`).

## Cutting a release

1. Run the bump suggester from the repo root:
   ```
   python3 scripts/suggest_version_bump.py
   ```
   It prints the last tag, how many commits were considered, the
   classified bump level (feat → minor, fix → patch, `!`/`BREAKING
   CHANGE:` → major), and the suggested next version.
2. Show the user the suggestion and ask them to confirm or override it —
   never tag/push without explicit confirmation; this is a hard-to-reverse,
   externally-visible action.
3. On confirmation: in `CHANGELOG.md`, rename `## [Unreleased]` to
   `## [X.Y.Z] — YYYY-MM-DD` (today's date) and add a fresh empty
   `## [Unreleased]` above it.
4. Commit that: `git commit -m "chore(release): vX.Y.Z"`.
5. Land the commit per this repo's normal rules (branch + PR if
   `commit-conventions` is installed — don't push the release commit
   straight to the default branch either).
6. After the release commit reaches the default branch, tag it and push
   the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`. This triggers the
   installed workflow, which publishes the GitHub Release.

## Backfilling existing tags

For tags that predate this skill and have no Release yet, dispatch the
workflow once per tag: ref = default branch, input `tag=v0.x.y`.

## Scope notes

- No secrets needed beyond the default `GITHUB_TOKEN`.
- Every installed file is generic: no repo name, owner, or path is
  hardcoded, so the same files work unmodified across repos (beyond the
  tag-scheme check above).
```

- [ ] **Step 2: Commit**

```bash
git add -A skills/
git commit -m "feat: rename changelog-releases-assistant skill to semver-release, add version-bump flow"
```

---

### Task 12: Update `plugin.json`, root `README.md`, `CHANGELOG.md`

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- None (plugin metadata and docs only).

- [ ] **Step 1: Update `plugin.json`**

```json
{
  "name": "whiting",
  "displayName": "Whiting",
  "version": "0.2.0",
  "description": "Bootstraps a repo's release discipline end to end: repo init, Conventional Commits enforcement, semver-driven version bumps, and CHANGELOG-driven GitHub Releases — plus an inspect skill to audit and retrofit existing repos.",
  "author": {
    "name": "Lux Solari",
    "email": "luxsolari@outlook.com"
  },
  "homepage": "https://github.com/luxsolari/whiting",
  "repository": "https://github.com/luxsolari/whiting",
  "license": "MIT",
  "keywords": ["github-releases", "changelog", "keep-a-changelog", "conventional-commits", "semver", "repo-init", "git-hooks", "agents-md", "automation"]
}
```

- [ ] **Step 2: Rewrite `README.md`**

```markdown
# Whiting

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code plugin that bootstraps a repo's whole release discipline:
init the repo, enforce Conventional Commits, derive semver bumps from
commit history, and publish GitHub Releases straight from `CHANGELOG.md`.
Named after Charlie Whiting, F1's longtime Race Director — famous for
strictly enforcing the rulebook.

## What it does

Four focused skills, one per lifecycle stage:

- **`inspect`** — audits an existing repo against these conventions
  (changelog format, tag scheme, existing automation, commit style,
  hook activation, AGENTS.md/CLAUDE.md, branch protection) and reports a
  concrete remediation plan. Read-only, never writes.
- **`repo-init`** — bootstraps the baseline: `git init` if needed,
  `LICENSE`, `README.md`, and a Keep a Changelog `CHANGELOG.md`.
- **`commit-conventions`** — installs a `commit-msg` hook (Conventional
  Commits) and a `pre-push` hook (blocks direct pushes to the default
  branch), and generates `AGENTS.md` (the rules) with `CLAUDE.md`
  importing it.
- **`semver-release`** — suggests the next version from commits since the
  last tag, and publishes a GitHub Release from the matching
  `CHANGELOG.md` section whenever that tag is pushed.

## Requirements

- A repo with (or being bootstrapped to have) a `CHANGELOG.md` following
  [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and tags in
  `v*.*.*` form. `inspect` and `repo-init` help you get there.
- `gh` CLI, authenticated, for anything that touches GitHub (Releases,
  reading the default branch, license text lookup).

## Install

```
/plugin marketplace add luxsolari/lux-solari-plugins
/plugin install whiting@lux-solari-plugins
```

Then, in any repo:

```
Audit this repo against whiting's conventions.
```

or, starting fresh:

```
Bootstrap this repo with whiting.
```

## This repo dogfoods itself

`scripts/`, `.github/workflows/release.yml`, `AGENTS.md`, and `CLAUDE.md`
here are exactly what the skills above install elsewhere — including this
repo's own commit-msg/pre-push hooks and its own releases.

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 3: Add a `CHANGELOG.md` `[Unreleased]` entry**

Insert directly below the `## [Unreleased]`-to-be header position — i.e. change the top of `CHANGELOG.md` from:

```markdown
---

## [0.1.0] — 2026-07-04
```

to:

```markdown
---

## [Unreleased]

### Added
- `inspect` skill: read-only audit of an existing repo against whiting's conventions (changelog format, tag scheme, existing release automation, commit style, hook activation, AGENTS.md/CLAUDE.md, branch protection), with a concrete remediation plan pointing at `repo-init`, `commit-conventions`, or `semver-release`.
- `repo-init` skill: bootstraps `LICENSE`, `README.md`, and a Keep a Changelog `CHANGELOG.md`, including `git init` for from-scratch repos.
- `commit-conventions` skill: installs a `commit-msg` hook enforcing Conventional Commits and a `pre-push` hook blocking direct pushes to the default branch (both via a tracked `scripts/hooks/` directory activated with `core.hooksPath`), and generates `AGENTS.md` (with `CLAUDE.md` importing it) documenting commit format, semver-bump discipline, changelog-first workflow, and the no-direct-push rule.
- `scripts/suggest_version_bump.py`: classifies commits since the last tag by Conventional Commit type/breaking-change footer and suggests the next semver version.
- `scripts/render_template.py`: generic `{{KEY}}` placeholder substitution used by `repo-init` and `commit-conventions` to render their bundled templates.

### Changed
- Renamed the plugin and its GitHub repo from `changelog-releases-assistant` to **whiting**; `changelog-releases-assistant`'s skill is renamed `semver-release` and extended with the bump-suggestion flow above. Clean-break rename, no compatibility alias.

## [0.1.0] — 2026-07-04
```

(Everything else in `CHANGELOG.md`, including the `[0.1.0]` section body and its reference link at the bottom, is untouched.)

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m "docs: rename plugin to whiting, document the four skills, add Unreleased entry"
```

---

### Task 13: Dogfood on this repo, then land the branch

**Files:**
- Create: `AGENTS.md` (this repo's root)
- Create: `CLAUDE.md` (this repo's root)

**Interfaces:**
- Consumes: `scripts/render_template.py`, `templates/AGENTS.md.tmpl`, `templates/CLAUDE.md.tmpl`, `scripts/hooks/commit-msg`, `scripts/hooks/pre-push` — all already present in this repo's own working tree from Tasks 3–6.

- [ ] **Step 1: Adopt the conventions on this repo**

```bash
git config whiting.defaultbranch main
git config core.hooksPath scripts/hooks
python3 scripts/render_template.py templates/AGENTS.md.tmpl DEFAULT_BRANCH=main > AGENTS.md
cp templates/CLAUDE.md.tmpl CLAUDE.md
```

- [ ] **Step 2: Verify the commit-msg hook is actually active**

Run: `git commit --allow-empty -m "this is not a conventional commit"`
Expected: rejected with the `commit-msg: rejected —` message from Task 4's hook.

Run: `git commit --allow-empty -m "docs: verify commit-msg hook is active on this repo"`
Expected: succeeds. This becomes a real commit in the branch's history.

- [ ] **Step 3: Verify the pre-push hook is actually active**

Run: `git push origin HEAD:main`
Expected: rejected locally, before any network call, with the `pre-push: rejected —` message from Task 5's hook. (The feature branch itself pushes fine in Step 4 below, since its remote ref isn't `main`.)

- [ ] **Step 4: Commit the dogfooding files**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "docs(rules): adopt commit-conventions rules for this repo"
```

- [ ] **Step 5: Push the branch and open a PR**

```bash
git push -u origin feat/whiting-rebrand
gh pr create --title "feat: rename to whiting, add inspect/repo-init/commit-conventions skills" --body "$(cat <<'EOF'
## Summary
- Renames changelog-releases-assistant to whiting.
- Adds inspect (audit), repo-init (bootstrap), and commit-conventions (Conventional Commits + no-direct-push hooks, AGENTS.md/CLAUDE.md) skills.
- Extends the existing release-publishing skill (now semver-release) with a commit-driven version-bump suggester.
- This repo adopts its own new conventions (AGENTS.md/CLAUDE.md, commit-msg/pre-push hooks).

## Test plan
- [x] scripts/run_tests.sh passes (unit tests for suggest_version_bump.py, render_template.py, template rendering, hook shell scripts)
- [x] commit-msg hook rejects a non-conforming message and accepts a conforming one, verified live on this branch
- [x] pre-push hook rejects a direct push to main, verified live on this branch
EOF
)"
```

- [ ] **Step 6: Confirm with the user, then merge**

**Pause here and get explicit confirmation before merging** — this is a hard-to-reverse, externally-visible action per this plan's Global Constraints.

```bash
gh pr merge --squash --delete-branch
```

- [ ] **Step 7: Verify main is clean**

```bash
git checkout main
git pull
sh scripts/run_tests.sh
```
Expected: `All tests passed.`

---

### Task 14: Rename the GitHub repo, update the marketplace entry

**Files (in `~/Dev/lux-solari-plugins`):**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

**Interfaces:**
- None (external repo/GitHub metadata).

- [ ] **Step 1: Rename the GitHub repo**

**Pause here and get explicit confirmation before renaming** — this changes a shared, externally-visible resource per this plan's Global Constraints.

```bash
gh repo rename whiting
git remote set-url origin git@github.com:luxsolari/whiting.git
gh repo view luxsolari/whiting --json name,url
```
Expected: `{"name":"whiting","url":"https://github.com/luxsolari/whiting"}`

- [ ] **Step 2: Update the marketplace repo's entry**

In `~/Dev/lux-solari-plugins/.claude-plugin/marketplace.json`, change the `changelog-releases-assistant` entry:

```json
    {
      "name": "whiting",
      "description": "Bootstraps a repo's release discipline end to end: repo init, Conventional Commits enforcement, semver-driven version bumps, and CHANGELOG-driven GitHub Releases — plus an inspect skill to audit and retrofit existing repos.",
      "author": {
        "name": "Lux Solari",
        "email": "luxsolari@outlook.com"
      },
      "homepage": "https://github.com/luxsolari/whiting",
      "repository": "https://github.com/luxsolari/whiting",
      "license": "MIT",
      "keywords": ["github-releases", "changelog", "keep-a-changelog", "conventional-commits", "semver", "repo-init", "git-hooks", "agents-md", "automation"],
      "category": "productivity",
      "source": {
        "source": "github",
        "repo": "luxsolari/whiting"
      }
    }
```

In `README.md`, update the corresponding install snippet from
`claude plugins install changelog-releases-assistant@lux-solari-plugins`
to `claude plugins install whiting@lux-solari-plugins`, and its
description blurb to match the new plugin.json description above.

- [ ] **Step 3: Commit and push**

**Pause here and get explicit confirmation before pushing** — this pushes to a separate, shared repo per this plan's Global Constraints.

```bash
cd ~/Dev/lux-solari-plugins
git add .claude-plugin/marketplace.json README.md
git commit -m "chore: rename changelog-releases-assistant to whiting"
git push
```

- [ ] **Step 4: Return to the whiting repo**

```bash
cd ~/Dev/whiting
```

(Path changes because `gh repo rename` doesn't rename the local directory — this is just a `cd`, not a file operation.)

---

### Task 15: Cut the `v0.2.0` release (dogfooding `semver-release`)

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `scripts/suggest_version_bump.py` (Tasks 1–2).

- [ ] **Step 1: Run the bump suggester**

```bash
python3 scripts/suggest_version_bump.py
```
Expected: reports `Bump level: minor` and `Suggested next version: v0.2.0` (the merged PR's commits are dominated by `feat:` commits with no breaking changes, per Task 1's classification rules).

- [ ] **Step 2: Confirm with the user**

**Pause here and get explicit confirmation of the version number before proceeding** — tagging and publishing a release is hard to reverse and externally visible.

- [ ] **Step 3: Update the changelog and branch**

```bash
git checkout -b chore/release-v0.2.0
```

In `CHANGELOG.md`, change:
```markdown
## [Unreleased]
```
to:
```markdown
## [Unreleased]

## [0.2.0] — 2026-07-04
```
(i.e. add a fresh empty `## [Unreleased]` above, and rename the section that held this plan's entries to `## [0.2.0] — 2026-07-04`.)

At the bottom of `CHANGELOG.md`, add the reference link next to the existing `[0.1.0]` one:
```markdown
[0.2.0]: https://github.com/luxsolari/whiting/releases/tag/v0.2.0
```

- [ ] **Step 4: Commit and land it**

```bash
git add CHANGELOG.md
git commit -m "chore(release): v0.2.0"
git push -u origin chore/release-v0.2.0
gh pr create --title "chore(release): v0.2.0" --body "Cuts v0.2.0 per scripts/suggest_version_bump.py."
```

**Pause here and get explicit confirmation before merging.**

```bash
gh pr merge --squash --delete-branch
```

- [ ] **Step 5: Tag and push**

```bash
git checkout main
git pull
```

**Pause here and get explicit confirmation before tagging/pushing** — this triggers the public release.

```bash
git tag v0.2.0
git push origin v0.2.0
```

- [ ] **Step 6: Verify the release published**

```bash
gh run list --limit 3
gh release view v0.2.0
```
Expected: the latest `Release` workflow run shows `success`, and `gh release view v0.2.0` shows a body matching the `[0.2.0]` CHANGELOG section from Step 3.

---

## Self-Review Notes

- **Spec coverage**: every section of `docs/superpowers/specs/2026-07-04-whiting-plugin-design.md` maps to a task — identity/repo (Task 12, 14), `inspect` (7–8), `repo-init` (6, 9), `commit-conventions` (4–6, 10), `semver-release` (1–2, 11), migration mechanics (13–14), release-cut verification (15).
- **Placeholder scan**: no TBD/TODO in any step; the two `<!-- Add ... here. -->` lines are literal *content* of the generated `README.md.tmpl` scaffold (an intentional fill-in-later marker for end users of `repo-init`, not an unfinished plan step).
- **Type/name consistency checked**: `classify_bump`/`next_version` signatures introduced in Task 1 are used identically in Task 2 and referenced identically in Task 11's `SKILL.md` prose; `render()` from Task 3 is used identically in Task 6's test and Tasks 9–10's `SKILL.md` prose; `whiting.defaultbranch` config key is set in Task 10's `SKILL.md` and Task 13's Step 1, and read in Task 5's hook and Task 7's `inspect_repo.sh` — same key name throughout.
