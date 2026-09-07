---
name: repo-init
description: >-
  Bootstrap a repo's baseline — git init if needed, LICENSE, README.md
  skeleton, a Keep a Changelog-formatted CHANGELOG.md, and the agent
  rule files (AGENTS.md, CLAUDE.md importing it, JOURNAL.md) — whether
  starting from an empty directory or filling gaps in an existing repo.
  Use when the user wants to start a new project properly or is missing
  one of these files. Never overwrites an existing file without asking.
license: MIT
---

# repo-init

Bootstraps the baseline every other whiting skill assumes is there: a git
repo, a LICENSE, a README, a Keep a Changelog `CHANGELOG.md`, and the
agent rule files — `AGENTS.md`, a `CLAUDE.md` that imports it, and the
`JOURNAL.md` work log those rules refer to.

## When to use this skill

- "Set up a new repo for this project."
- "Bootstrap this directory properly."
- "We're missing a LICENSE/CHANGELOG, can you add one?"

## Before touching anything

1. Run `git rev-parse --is-inside-work-tree`. If it fails, this is a
   from-scratch bootstrap — run `git init` before anything else.
2. Check for existing `LICENSE`, `README.md`, `CHANGELOG.md`,
   `AGENTS.md`, `CLAUDE.md`, `JOURNAL.md`. For each one that already
   exists, report it and ask before touching it — never overwrite
   silently. Skip files the user says to leave alone.
   `AGENTS.md` and `CLAUDE.md` are the exception to "ask, then skip":
   when they already exist they get *merged*, not replaced (see below),
   so nothing the repo already says is lost.

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
| `README.md` | `templates/README.md.tmpl` | `PROJECT_NAME`, `DESCRIPTION`, `REPO_SLUG`, `LICENSE_NAME` |
| `LICENSE` (MIT) | `templates/LICENSE-MIT.tmpl` | `YEAR`, `AUTHOR` |
| `AGENTS.md` | `templates/AGENTS.md.tmpl` | `DEFAULT_BRANCH` |
| `CLAUDE.md` | `templates/CLAUDE.md.tmpl` | none |
| `JOURNAL.md` | `templates/JOURNAL.md.tmpl` | `DATE` |

For the three agent files, follow the same procedure `commit-conventions`
uses — it owns them:

- `AGENTS.md`: render `AGENTS.md.tmpl` with the repo's default branch
  (`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`,
  falling back to `main`). If the file already exists, merge instead of
  overwriting, so only the missing sections are appended:

  ```
  python3 $CLAUDE_PLUGIN_ROOT/scripts/merge_agents_md.py \
    AGENTS.md /tmp/whiting-agents.md --report   # then, to apply, drop --report
  ```

- `CLAUDE.md`: create it as the single line `@AGENTS.md`; if it exists
  and doesn't already reference `AGENTS.md`, prepend that line and leave
  the rest alone.
- `JOURNAL.md`: render with `DATE="$(date +%F)"`, only if missing. If a
  `BITACORA.md` is present instead, it is the same log under its pre-0.6.0
  name — rename it (`git mv BITACORA.md JOURNAL.md`) and render nothing.
  Two work logs in one repo is worse than either name.

See `commit-conventions` for the full merge walkthrough, including how
headings are matched.

For `README.md`, ask the user for the project name and a one-line
description. Derive `REPO_SLUG` (`owner/repo`) from the remote —
`git remote get-url origin`, taking the `owner/repo` out of the SSH or
HTTPS GitHub URL; if there is no remote yet, ask the user for it. Set `LICENSE_NAME` to the shields-escaped license id. For `MIT` it is
just `MIT`; for any other license do not hand-escape — run the id
through the helper so the badge label is always correct:

    LICENSE_NAME=$(python3 $CLAUDE_PLUGIN_ROOT/scripts/shields_escape.py "Apache-2.0")  # -> Apache--2.0

Then render:

```
python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
  $CLAUDE_PLUGIN_ROOT/templates/README.md.tmpl \
  PROJECT_NAME="my-project" DESCRIPTION="What it does, one line." \
  REPO_SLUG="owner/my-project" LICENSE_NAME="MIT" > README.md
```

The Version badge shows "no releases" until the first tag is pushed —
the expected state for a new repo, and it self-populates once
`semver-release` cuts a release.

For `LICENSE`, ask which license (default MIT). If MIT, render
`LICENSE-MIT.tmpl` with the current year and the user's name. For any
other license, fetch the canonical text instead of guessing:
`gh api "licenses/<spdx-id>" --jq .body > LICENSE` (e.g. `apache-2.0`,
`gpl-3.0`).

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

## Land the change

If this is a from-scratch bootstrap, this is the first commit:
`git add -A && git commit -m "chore: initial commit"` — a valid
Conventional Commits subject even before the `commit-conventions` hook
exists to enforce it.

If retrofitting an existing, non-empty repo, land these files the same
way any other change lands there: branch, commit, PR — don't push
straight to the default branch.

## Next steps

After this, run `commit-conventions` to install the commit-message and
pre-push hooks that the rules in `AGENTS.md` refer to, then
`semver-release` to wire up release automation. `inspect` can tell you if either is already partially
in place.
