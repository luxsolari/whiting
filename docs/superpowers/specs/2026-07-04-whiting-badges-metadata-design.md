# Design: README badges + GitHub repo metadata

**Date:** 2026-07-04
**Status:** Approved
**Target version:** v0.3.0 (minor — new `feat`)

## Problem

When whiting bootstraps a repo it produces a bare README and leaves the
GitHub project page identity blank: no Version/License badges, no repo
description, no topics. Real repos want all three, and setting them by
hand every time defeats the point of a bootstrap tool. `inspect` also has
no way to flag their absence on an existing repo.

## Goal

Teach whiting to produce, on every repo it sets up, what a maintainer
would otherwise add by hand:

1. Version + License shields.io badges in the README.
2. A GitHub repo description.
3. GitHub repo topics.

And teach `inspect` to warn when any of the three is missing.

## Non-goals

- Auto-deriving *good* topics from repo contents. Topics are prompted
  from the user, like `PROJECT_NAME`/`DESCRIPTION` already are.
- Supporting badge providers other than shields.io.
- Retroactively editing badges into a README that already has some.

## Design

### 1. Badges in the README template

`templates/README.md.tmpl` gains two badge lines under the H1, matching
whiting's own README convention:

```
# {{PROJECT_NAME}}

[![Version](https://img.shields.io/github/v/release/{{REPO_SLUG}})](https://github.com/{{REPO_SLUG}}/releases)
[![License: {{LICENSE_NAME}}](https://img.shields.io/badge/license-{{LICENSE_NAME}}-blue.svg)](LICENSE)

{{DESCRIPTION}}
```

Two new placeholders, both required by `render_template.py` (which errors
on any unsupplied `{{KEY}}`), so `repo-init` must always pass them:

- `REPO_SLUG` — `owner/repo`. `repo-init` derives it from
  `git remote get-url origin` (parse the `owner/repo` out of the SSH or
  HTTPS GitHub URL). If there is no remote yet (from-scratch bootstrap),
  `repo-init` asks the user for `owner/repo`. The version badge harmlessly
  renders "no releases" until the first tag — the expected state for a new
  repo.
- `LICENSE_NAME` — defaults to `MIT`. For a non-MIT license it is the SPDX
  id with hyphens doubled for shields' label escaping (e.g. `Apache-2.0`
  → `Apache--2.0`). The badge always links to the local `LICENSE` file.

### 2. `repo-init` sets description + topics (Approach A)

`repo-init` already prompts for the one-line description and writes the
README; it is the cohesive home for repo-identity setup. After the files
land, `repo-init` gains a metadata step:

- Gate: only if a GitHub remote exists **and** `gh auth status` succeeds.
  Otherwise print a one-line note that description/topics can be set later
  (with the exact `gh repo edit` command), and stop — never fail.
- Description: reuse the one-line `DESCRIPTION` already collected for the
  README (no second prompt).
- Topics: prompt the user once for a comma/space-separated list, then
  `gh repo edit "<slug>" --description "<desc>" --add-topic t1 --add-topic t2 ...`.

`SKILL.md` updates: extend the placeholder table with `REPO_SLUG` and
`LICENSE_NAME`, and document the metadata step and its remote/gh gate.

### 3. `inspect` flags all three

`scripts/inspect_repo.sh` gains three checks, following the existing
best-effort gh-gated pattern used for branch protection (warn, never
fail; skip cleanly when `gh` is unauthenticated or there is no remote):

- **Badges:** `grep -q 'img\.shields\.io' README.md` → ok / warn
  ("README has no shields.io badges"). Offline, no gh needed.
- **Description:** `gh repo view --json description -q .description`
  non-empty → ok / warn. gh-gated.
- **Topics:** `gh repo view --json repositoryTopics` has ≥1 topic →
  ok / warn. gh-gated.

`inspect/SKILL.md` updates: mention the three new checks and route the
remediation to `repo-init`.

### 4. Tests

- `tests/test_render_template.py` / `tests/test_templates_render.py`:
  supply the two new placeholders and assert both badge lines render with
  the substituted slug and license name; assert no stray `{{...}}`
  remains.
- `tests/test_inspect_repo.sh`: add an offline case asserting the badge
  check warns on a README with no badge and passes on one with a
  shields.io badge. The description/topics checks are gh-gated and match
  the branch-protection test's existing offline handling (not asserted
  against a live gh).

## Landing

Land in `luxsolari/whiting` via branch → PR (its own hooks enforce
Conventional Commits and block direct pushes to `main`). This is a `feat`
→ minor bump **v0.2.0 → v0.3.0**. Add an `### Added` entry under
`## [Unreleased]` in `CHANGELOG.md`, then after merge tag `v0.3.0` (moving
the `[Unreleased]` content into a `## [0.3.0]` section and updating the
link references) to fire the release workflow.

## Risks

- **Placeholder breakage:** adding required placeholders to the template
  breaks any current caller that renders it without them — but the only
  caller is `repo-init`, updated in the same change, and the render tests
  cover it.
- **shields label escaping:** only affects non-MIT SPDX ids with hyphens;
  documented in `repo-init` and defaulted to the common MIT case.
