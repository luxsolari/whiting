# README Badges + GitHub Repo Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach whiting to add Version/License badges to the READMEs it generates, set the GitHub repo description + topics during `repo-init`, and flag all three in `inspect`.

**Architecture:** Two new required placeholders (`REPO_SLUG`, `LICENSE_NAME`) in `templates/README.md.tmpl`, supplied by `repo-init`; a gated `gh repo edit` metadata step documented in `repo-init/SKILL.md`; three best-effort checks added to `inspect_repo.sh` mirroring its existing gh-gated branch-protection pattern.

**Tech Stack:** POSIX sh, Python 3 (`unittest`), shell test harness, `gh` CLI, shields.io.

## Global Constraints

- Land in the `luxsolari/whiting` repo via branch → PR; never push straight to `main` (its `pre-push` hook + server-side protection enforce this).
- Commit subjects MUST be Conventional Commits (its `commit-msg` hook enforces this).
- `render_template.py` errors on any unsupplied `{{KEY}}` — every placeholder added to a template MUST be supplied by its caller and by the render test.
- New `inspect_repo.sh` checks are best-effort: `report_warn` (never `report_fail`) when missing, and skip cleanly when `gh` is unauthenticated or there is no origin remote.
- `inspect_repo.sh` runs under `set -u` (no `set -e`); keep the existing `|| true` / default-value style.
- shields.io label escaping: `LICENSE_NAME` uses the SPDX id with hyphens doubled (e.g. `Apache--2.0`); default is `MIT`.
- Run the full suite with `sh scripts/run_tests.sh` from the repo root before the PR.

---

### Task 1: Badges in the README template

**Files:**
- Modify: `templates/README.md.tmpl` (add two badge lines under the H1)
- Test: `tests/test_templates_render.py` (existing `test_readme_template_renders_with_project_fields`)

**Interfaces:**
- Consumes: `render_template.render(text, mapping)` from `scripts/render_template.py`.
- Produces: `templates/README.md.tmpl` now requires the mapping keys `PROJECT_NAME`, `DESCRIPTION`, `REPO_SLUG`, `LICENSE_NAME`. `repo-init` (Task 3) relies on these exact key names.

- [ ] **Step 1: Update the render test to supply the new placeholders and assert badges**

Replace `test_readme_template_renders_with_project_fields` in `tests/test_templates_render.py` with:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_templates_render.TestTemplatesRender.test_readme_template_renders_with_project_fields -v`
Expected: FAIL — the template lacks the badge URLs, and `render` raises `KeyError` for the unused-but-now-passed keys is NOT the failure (extra keys are allowed); the failure is `AssertionError` on the missing shields.io URL.

- [ ] **Step 3: Add the badge lines to the template**

Edit `templates/README.md.tmpl` so the top becomes exactly:

```
# {{PROJECT_NAME}}

[![Version](https://img.shields.io/github/v/release/{{REPO_SLUG}})](https://github.com/{{REPO_SLUG}}/releases)
[![License: {{LICENSE_NAME}}](https://img.shields.io/badge/license-{{LICENSE_NAME}}-blue.svg)](LICENSE)

{{DESCRIPTION}}
```

Leave the rest of the file (`## Install`, `## Usage`, `## License`) unchanged.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_templates_render.TestTemplatesRender.test_readme_template_renders_with_project_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/README.md.tmpl tests/test_templates_render.py
git commit -m "feat(repo-init): add version and license badges to README template"
```

---

### Task 2: inspect flags badges, description, and topics

**Files:**
- Modify: `scripts/inspect_repo.sh` (add badge check; extend the gh block with description/topics)
- Modify: `skills/inspect/SKILL.md` (document the three new checks)
- Test: `tests/test_inspect_repo.sh` (assert the offline badge check)

**Interfaces:**
- Consumes: existing `report_ok` / `report_warn` helpers and the `repo_slug` derivation already present in the gh block of `scripts/inspect_repo.sh`.
- Produces: three new report lines with these exact strings (the test and remediation prose depend on them): `README.md has shields.io badges` / `README.md has no shields.io badges`; `GitHub repo description set` / `GitHub repo description not set`; `GitHub repo topics set (N)` / `GitHub repo topics not set`.

- [ ] **Step 1: Update the inspect test — Case 3 README gets a badge, add an assertion**

In `tests/test_inspect_repo.sh`, in Case 3 ("fully compliant repo"), replace the line:

```sh
    touch LICENSE README.md
```

with:

```sh
    touch LICENSE
    printf '# demo\n\n[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)\n' > README.md
```

Then, in Case 3's assertion block (after the `core.hooksPath set` assertion), add:

```sh
printf '%s\n' "$out" | grep -q "README.md has shields.io badges" || { echo "FAIL: expected badge check ok"; fail=1; }
```

- [ ] **Step 2: Run the inspect test to verify it fails**

Run: `sh tests/test_inspect_repo.sh`
Expected: FAIL with `FAIL: expected badge check ok` (the script does not emit that line yet).

- [ ] **Step 3: Add the offline badge check to inspect_repo.sh**

In `scripts/inspect_repo.sh`, immediately AFTER the `AGENTS.md` check block (the one ending `report_warn "AGENTS.md missing"` / `fi`) and BEFORE the `if command -v gh ...` block, insert:

```sh
if [ -f README.md ]; then
    if grep -q 'img\.shields\.io' README.md; then
        report_ok "README.md has shields.io badges"
    else
        report_warn "README.md has no shields.io badges"
    fi
fi
```

- [ ] **Step 4: Extend the gh block with description + topics checks**

In `scripts/inspect_repo.sh`, replace the entire existing gh block:

```sh
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
```

with:

```sh
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    origin_url=$(git config --get remote.origin.url || true)
    repo_slug=$(printf '%s' "$origin_url" | sed -E 's#.*[:/]([^/]+/[^/]+)(\.git)?$#\1#')

    if [ -n "$repo_slug" ] && gh api "repos/$repo_slug/branches/$default_branch/protection" >/dev/null 2>&1; then
        report_ok "GitHub branch protection enabled on '$default_branch'"
    else
        report_warn "GitHub branch protection not detected on '$default_branch' (or gh lacks admin read access)"
    fi

    if [ -n "$repo_slug" ]; then
        description=$(gh repo view "$repo_slug" --json description -q '.description // ""' 2>/dev/null || true)
        if [ -n "$description" ]; then
            report_ok "GitHub repo description set"
        else
            report_warn "GitHub repo description not set"
        fi
        topic_count=$(gh repo view "$repo_slug" --json repositoryTopics -q '.repositoryTopics | length' 2>/dev/null || echo 0)
        if [ "${topic_count:-0}" -gt 0 ]; then
            report_ok "GitHub repo topics set ($topic_count)"
        else
            report_warn "GitHub repo topics not set"
        fi
    else
        report_warn "no origin remote — skipped GitHub description/topics check"
    fi
else
    report_warn "gh not authenticated — skipped branch protection and metadata checks"
fi
```

- [ ] **Step 5: Run the inspect test to verify it passes**

Run: `sh tests/test_inspect_repo.sh`
Expected: PASS — `All inspect_repo.sh tests passed.` (Case 3 has no origin remote, so description/topics take the "skipped" branch; only the offline badge line is asserted.)

- [ ] **Step 6: Document the new checks in inspect/SKILL.md**

In `skills/inspect/SKILL.md`, in the "What it does" bulleted list, add three bullets (matching the existing ✅/⚠️ phrasing style):

```markdown
- Whether `README.md` carries shields.io badges (Version/License).
- Whether the GitHub repo has a description set (best-effort; skipped if
  `gh` isn't authenticated or there's no origin remote).
- Whether the GitHub repo has topics set (same best-effort gating).
```

Then, in the "After running it" remediation section, add a line routing these to `repo-init`:

```markdown
- Missing README badges, GitHub description, or topics → run `repo-init`
  (it renders badges into the README and sets description/topics via
  `gh repo edit`).
```

- [ ] **Step 7: Commit**

```bash
git add scripts/inspect_repo.sh tests/test_inspect_repo.sh skills/inspect/SKILL.md
git commit -m "feat(inspect): flag missing README badges, description, and topics"
```

---

### Task 3: repo-init supplies badges and sets description + topics

**Files:**
- Modify: `skills/repo-init/SKILL.md` (placeholder table, slug/license guidance, metadata step)

**Interfaces:**
- Consumes: the `REPO_SLUG` / `LICENSE_NAME` placeholder contract from Task 1 and the report strings from Task 2 (for the "Next steps" cross-reference).
- Produces: documented `repo-init` behavior; no code interface for later tasks.

This task is documentation only (SKILL.md is executed by the agent, not unit-tested). It ends in a commit.

- [ ] **Step 1: Extend the placeholder table**

In `skills/repo-init/SKILL.md`, in the "What to install" table, change the `README.md` row's Placeholders cell to:

```
`PROJECT_NAME`, `DESCRIPTION`, `REPO_SLUG`, `LICENSE_NAME`
```

- [ ] **Step 2: Replace the README render example with one that supplies all four placeholders and derives the slug**

Replace the paragraph + code block that currently reads "For `README.md`, ask the user for the project name and a one-line description before rendering:" and its `render_template.py ... PROJECT_NAME=... DESCRIPTION=...` example with:

````markdown
For `README.md`, ask the user for the project name and a one-line
description. Derive `REPO_SLUG` (`owner/repo`) from the remote —
`git remote get-url origin`, taking the `owner/repo` out of the SSH or
HTTPS GitHub URL; if there is no remote yet, ask the user for it. Set
`LICENSE_NAME` to the license id (`MIT` by default; for another license
use its SPDX id with hyphens doubled for the shields badge, e.g.
`Apache--2.0`). Then render:

```
python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
  $CLAUDE_PLUGIN_ROOT/templates/README.md.tmpl \
  PROJECT_NAME="my-project" DESCRIPTION="What it does, one line." \
  REPO_SLUG="owner/my-project" LICENSE_NAME="MIT" > README.md
```

The Version badge shows "no releases" until the first tag is pushed —
the expected state for a new repo, and it self-populates once
`semver-release` cuts a release.
````

- [ ] **Step 3: Add the GitHub metadata step**

In `skills/repo-init/SKILL.md`, add a new `## Set GitHub description and topics` section immediately before `## Land the change`:

````markdown
## Set GitHub description and topics

Once the repo has a GitHub remote, give its project page an identity.
Only do this if a remote exists **and** `gh` is authenticated
(`git remote get-url origin` succeeds and `gh auth status` succeeds);
otherwise skip it and tell the user they can run it later, printing the
command below for them.

Reuse the one-line description already collected for the README as the
GitHub description, and ask the user for a short list of topics
(space-separated, lowercase, hyphenated — e.g. `claude-code cli automation`):

```
gh repo edit "owner/repo" \
  --description "What it does, one line." \
  --add-topic topic-one --add-topic topic-two
```

Never fail the skill if this step can't run — it is additive polish on
top of the committed files.
````

- [ ] **Step 4: Commit**

```bash
git add skills/repo-init/SKILL.md
git commit -m "docs(repo-init): document badge placeholders and GitHub metadata step"
```

---

### Task 4: Changelog entry

**Files:**
- Modify: `CHANGELOG.md` (add an `### Added` entry under `## [Unreleased]`)

**Interfaces:** none.

- [ ] **Step 1: Add the Unreleased entry**

In `CHANGELOG.md`, change the `## [Unreleased]` section (currently empty) to:

```markdown
## [Unreleased]

### Added
- `repo-init` now renders Version and License shields.io badges into the
  generated `README.md` (new `REPO_SLUG` / `LICENSE_NAME` template
  placeholders) and, when a GitHub remote and `gh` auth are available,
  sets the repo description and topics via `gh repo edit`.
- `inspect` now flags missing README badges (offline) and a missing
  GitHub description or topics (best-effort, gh-gated).
```

- [ ] **Step 2: Run the full suite**

Run: `sh scripts/run_tests.sh`
Expected: all tests pass (Python render tests + shell inspect/hook tests).

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for badges and repo metadata"
```

---

### Task 5: Robust shields.io escaping helper

**Files:**
- Create: `scripts/shields_escape.py`
- Test: `tests/test_shields_escape.py`
- Modify: `skills/repo-init/SKILL.md` (rewire `LICENSE_NAME` derivation to run the helper)
- Modify: `CHANGELOG.md` (note the helper under the existing `## [Unreleased]` entry)

**Interfaces:**
- Produces: `shields_escape(label: str) -> str` in `scripts/shields_escape.py`, and a CLI `python3 scripts/shields_escape.py "<label>"` that prints the escaped label with no trailing newline. `repo-init` (doc) calls the CLI to compute `LICENSE_NAME`.
- Rationale: `render_template.py` stays a generic literal substitutor; shields label escaping is a property of the value, computed before substitution — not renderer logic.

- [ ] **Step 1: Write the failing test**

Create `tests/test_shields_escape.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_shields_escape -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shields_escape'`.

- [ ] **Step 3: Write the helper**

Create `scripts/shields_escape.py`:

```python
#!/usr/bin/env python3
"""Escape a label for a shields.io static badge.

shields treats '-', '_' and space specially in the label/message segments:
a literal '-' is written '--', a literal '_' is written '__', and a space
is written '_'. SPDX license ids (e.g. Apache-2.0, BSD-3-Clause) need this
so their hyphens survive into the badge.
"""
import sys


def shields_escape(label):
    return label.replace("_", "__").replace("-", "--").replace(" ", "_")


def main():
    if len(sys.argv) != 2:
        print("Usage: shields_escape.py <label>", file=sys.stderr)
        return 1
    print(shields_escape(sys.argv[1]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make it executable: `chmod +x scripts/shields_escape.py`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_shields_escape -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Rewire repo-init to run the helper**

In `skills/repo-init/SKILL.md`, replace the sentence:

```
Set
`LICENSE_NAME` to the license id (`MIT` by default; for another license
use its SPDX id with hyphens doubled for the shields badge, e.g.
`Apache--2.0`). Then render:
```

with:

```
Set `LICENSE_NAME` to the shields-escaped license id. For `MIT` it is
just `MIT`; for any other license do not hand-escape — run the id
through the helper so the badge label is always correct:

    LICENSE_NAME=$(python3 $CLAUDE_PLUGIN_ROOT/scripts/shields_escape.py "Apache-2.0")  # -> Apache--2.0

Then render:
```

Leave the render code block and the "no releases" caveat that follow unchanged.

- [ ] **Step 6: Note the helper in the changelog**

In `CHANGELOG.md`, under the existing `## [Unreleased]` → `### Added` block, append one bullet:

```markdown
- `scripts/shields_escape.py` escapes the license id for the shields badge, so non-MIT SPDX ids (e.g. `Apache-2.0` → `Apache--2.0`) render correctly; `repo-init` runs it to compute `LICENSE_NAME`.
```

- [ ] **Step 7: Run the full suite and commit**

Run: `sh scripts/run_tests.sh`
Expected: `All tests passed.` (now including `test_shields_escape.py`).

```bash
git add scripts/shields_escape.py tests/test_shields_escape.py skills/repo-init/SKILL.md CHANGELOG.md
git commit -m "feat(repo-init): add shields_escape helper for license badge ids"
```

---

## Landing & release (after all tasks, human-gated)

These steps are outward-facing and run once, after the tasks above:

1. Push the branch and open a PR into `luxsolari/whiting`:
   `git push -u origin feat/readme-badges-repo-metadata` then `gh pr create`.
2. Merge the PR (squash). This is a `feat` → **minor bump v0.2.0 → v0.3.0**.
3. Cut the release: rename `## [Unreleased]` to `## [0.3.0] — <date>` (add a
   fresh empty `## [Unreleased]` above it), add a
   `[0.3.0]: https://github.com/luxsolari/whiting/releases/tag/v0.3.0` line to
   the reference-link block at the bottom of `CHANGELOG.md`, land that via its
   own PR, then `git tag v0.3.0 && git push origin v0.3.0` to fire the release
   workflow.

## Self-review notes

- **Spec coverage:** badges (Task 1), description+topics (Task 3), inspect flags (Task 2), tests (Tasks 1–2, plus full-suite gate in Task 4), landing/v0.3.0 (Landing section). All spec sections mapped.
- **Placeholder/type consistency:** placeholder names `REPO_SLUG`/`LICENSE_NAME` and inspect report strings are identical across the template, the render test, `repo-init/SKILL.md`, and `inspect_repo.sh`/its test.
- **Corrected from spec:** the spec named both `test_render_template.py` and `test_templates_render.py`; only `test_templates_render.py` renders the README template, so only it is touched (`test_render_template.py` tests the generic `render()` and needs no change).
