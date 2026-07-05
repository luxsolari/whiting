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
- Whether `README.md` carries shields.io badges (Version/License).
- Whether the GitHub repo has a description set (best-effort; skipped if
  `gh` isn't authenticated or there's no origin remote).
- Whether the GitHub repo has topics set (same best-effort gating).

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
- Missing README badges, GitHub description, or topics → run `repo-init`
  (it renders badges into the README and sets description/topics via
  `gh repo edit`).

## Scope notes

- This skill never writes files. It only reads and reports — all changes
  happen when you subsequently invoke `repo-init`, `commit-conventions`,
  or `semver-release`.
- If it reports an existing competing release-publishing workflow, tell
  the user and stop — don't invoke `semver-release` to add a second one.
