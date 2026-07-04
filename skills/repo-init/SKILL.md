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
