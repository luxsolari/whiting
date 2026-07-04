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
