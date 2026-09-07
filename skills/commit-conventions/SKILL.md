---
name: commit-conventions
description: >-
  Install Conventional Commits enforcement (a commit-msg hook) and a
  no-direct-push-to-main guard (a pre-push hook), plus generate AGENTS.md
  and CLAUDE.md rule files covering working-agreement defaults (register,
  answer scope, disagreement, language, JOURNAL.md work log) plus commit
  format, semver-bump discipline, changelog-first workflow, and branch
  protection policy — merging into existing files instead of replacing
  them. Use when the user wants commit conventions enforced or wants
  Claude/agents to follow a documented rule set in this repo.
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
  content — merge into it instead (see step 4/5 below). A repo that
  already has these files keeps every word it has; whiting only adds
  what's missing.

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

4. Write `AGENTS.md`. Render the template first, into a scratch file:

   ```
   python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
     $CLAUDE_PLUGIN_ROOT/templates/AGENTS.md.tmpl \
     DEFAULT_BRANCH="main" > /tmp/whiting-agents.md
   ```

   - **No `AGENTS.md` yet**: move the rendered file into place.
   - **`AGENTS.md` already exists**: merge, never replace. Existing
     content is the repo's own and stays untouched; only the sections it
     is missing get appended, in template order:

     ```
     python3 $CLAUDE_PLUGIN_ROOT/scripts/merge_agents_md.py \
       AGENTS.md /tmp/whiting-agents.md --report
     ```

     That prints one `present:`/`missing:` line per template section.
     Show it to the user, then apply the merge:

     ```
     python3 $CLAUDE_PLUGIN_ROOT/scripts/merge_agents_md.py \
       AGENTS.md /tmp/whiting-agents.md > /tmp/whiting-agents-merged.md \
       && mv /tmp/whiting-agents-merged.md AGENTS.md
     ```

     Sections are matched on their heading, ignoring case, punctuation,
     and anything past the first four words — so a repo that already
     says "No direct pushes to develop" keeps its own wording instead of
     getting a duplicate rule about `main`. If a repo's existing section
     covers the same ground under a heading whiting doesn't recognise,
     the merge will append a near-duplicate: read the result and
     reconcile the two by hand before committing.

5. Wire up `CLAUDE.md`:
   - If it doesn't exist: copy `templates/CLAUDE.md.tmpl` verbatim (it's
     just `@AGENTS.md`).
   - If it exists and doesn't already reference `AGENTS.md`: prepend the
     `@AGENTS.md` line, leaving the rest of the file untouched. Never
     move that repo's own instructions into `AGENTS.md` or delete them —
     the import is additive.

6. Create `JOURNAL.md` if it's missing — the work log the rule set
   refers to:

   ```
   python3 $CLAUDE_PLUGIN_ROOT/scripts/render_template.py \
     $CLAUDE_PLUGIN_ROOT/templates/JOURNAL.md.tmpl \
     DATE="$(date +%F)" > JOURNAL.md
   ```

   If it already exists, leave it alone.

## What AGENTS.md documents

Two groups of rules. The first is how agents work here at all — the
defaults every repo gets:

- **Register**: direct and concise, no preamble, no cheerleading.
- **Answer scope**: answer what was asked; offer adjacent detail in one
  line rather than appending it unbidden.
- **Disagreement**: don't agree automatically; verify claims instead of
  asking the user to confirm what could be looked up.
- **Language**: plain language over jargon; don't mix English technical
  terms into Spanish writing.
- **Work log**: append to `JOURNAL.md` after each task, read it before
  starting, compact it past ~40 entries.

The second is this repo's release discipline:

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

The template closes with a short note on the three-axes-framework plugin,
explaining what it covers so those rules aren't duplicated here. If that
plugin isn't in use, drop that last section — nothing else depends on it.

`AGENTS.md` is the only copy of these rules. `CLAUDE.md` imports it, so
Claude Code, Codex, and anything else that reads `AGENTS.md` all work
from the same file.

## Land the change

Branch, commit, PR — same rule the files themselves are about to start
enforcing.

## Next steps

Run `semver-release` next to wire up the version-bump-to-release pipeline
that `AGENTS.md`'s semver rule refers to.
