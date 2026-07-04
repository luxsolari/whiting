# Whiting plugin design

Renames and extends the `changelog-releases-assistant` plugin into `whiting`:
a repo-bootstrap and release-discipline plugin covering repo initialization,
Conventional Commits enforcement, semver-driven releases, and an audit skill
for retrofitting existing repos. Named after Charlie Whiting, F1's longtime
Race Director known for strictly enforcing the rulebook — continuing the
`hannah` naming convention (F1 domain figures whose real-world role maps to
the plugin's job).

## Scope

In scope:
- Rename this plugin and its GitHub repo to `whiting`.
- Split the existing single skill into four: `inspect`, `repo-init`,
  `commit-conventions`, `semver-release`.
- Add repo-from-scratch bootstrapping, a Conventional Commits git hook,
  semver bump suggestion, and generated `AGENTS.md`/`CLAUDE.md` rule files.
- Add a read-only audit skill (`inspect`) for existing repos.
- Update the `lux-solari-plugins` marketplace entry to match.

Out of scope:
- GitHub server-side branch protection configuration (admin/shared-infra
  change; the design only adds local `pre-push` enforcement).
- Any changes to the `sage-instructor` or `three-axes-framework` plugins.
- Backward-compatibility shim for the old `changelog-releases-assistant`
  name (clean break, per decision below).

## 1. Plugin identity & repo

- GitHub repo renamed: `luxsolari/changelog-releases-assistant` →
  `luxsolari/whiting` via `gh repo rename` (GitHub auto-redirects the old
  URL; existing clones' remotes keep working).
- `.claude-plugin/plugin.json`: `name: "whiting"`, `displayName: "Whiting"`,
  version bumped to `0.2.0`, description and keywords updated to cover
  repo-init, Conventional Commits, semver, and agent-rule generation.
- Clean-break rename: no alias or deprecated second entry for the old name.
  Justification: only `v0.1.0` has shipped, adoption is presumed near-zero,
  so compatibility baggage isn't worth carrying.

## 2. Skill: `inspect` (diagnostic, read-only)

**Purpose**: give a one-shot compliance picture of an *existing* repo
against `whiting`'s conventions, before deciding which of the other three
skills to run and with what adjustments. Consolidates what each skill's
"before touching anything" check does individually into one entry point —
the natural first move on a pre-existing, possibly messy repo.

**Checks performed** (all read-only, no writes):
- Git present, default branch name.
- `LICENSE`, `README.md` present?
- `CHANGELOG.md` present and Keep a Changelog-formatted (regex on
  `^## \[VERSION\]`)?
- Existing tag scheme (`v*.*.*` vs. something else).
- Existing release automation (grep for `gh release`,
  `softprops/action-gh-release`, `actions/create-release`, or similar) —
  avoid recommending a competing workflow.
- `core.hooksPath` git config + existing `commit-msg`/`pre-push` hooks.
- Sample of the last ~20 commit messages scored against Conventional
  Commits — gauges how disruptive the hook would be for existing
  contributors.
- Existing `CLAUDE.md`/`AGENTS.md` and whether they already cross-reference
  each other or contain conflicting rules.
- GitHub branch protection status on the default branch (read-only
  `gh api repos/:owner/:repo/branches/:branch/protection` call).

**Output**: a ✅/⚠️/❌ report per item, plus a concrete remediation plan
naming which of `repo-init` / `commit-conventions` / `semver-release` to
invoke and with what parameter adjustments (e.g., "tags use `release-`
prefix, not `v` — pass that to `semver-release` and adjust `release.yml`'s
tag glob accordingly").

**Boundary**: `inspect` never writes files. All remediation happens by
invoking the other three skills, parameterized by what `inspect` found —
keeps each skill's file ownership unambiguous.

## 3. Skill: `repo-init`

**Purpose**: bootstrap a repo's baseline, whether starting from an empty
directory or retrofitting an existing repo.

**Before touching anything**: check `git rev-parse --is-inside-work-tree`;
check for existing `LICENSE`, `README.md`, `CHANGELOG.md` and never
overwrite silently — report what's already there and ask before replacing.

**What it does**:
- `git init` if there's no repo yet.
- `LICENSE` — ask which license (default MIT) if missing.
- `README.md` skeleton if missing (title, description placeholder,
  install/usage stubs) — skipped for existing non-empty repos where one
  almost certainly exists.
- `CHANGELOG.md` skeleton in Keep a Changelog format, starting with an
  empty `## [Unreleased]` section.
- Initial commit if from scratch (`chore: initial commit` — valid
  Conventional Commits syntax even before the hook exists).
- Ends by pointing the user at `commit-conventions` and `semver-release` as
  the next two steps for full setup. No 4th orchestrator skill — chaining
  happens via each skill's "next step" pointer.

## 4. Skill: `commit-conventions`

**Purpose**: enforce Conventional Commits and generate the rule docs,
together (this pairing is why the skill split is by lifecycle stage, not by
artifact type).

**Key technical detail**: `.git/hooks/` isn't tracked by git, so a hook
copied straight there vanishes for every other clone/contributor. Instead:
- Hook scripts live in a **tracked** `scripts/hooks/commit-msg` and
  `scripts/hooks/pre-push`, plain POSIX sh, no Node/npm dependency.
- The skill runs `git config core.hooksPath scripts/hooks` to activate them
  for the current clone, and the generated `AGENTS.md` tells contributors
  to run that same line after cloning.

**Hooks installed**:
- `commit-msg` — regex-validates `type(scope)!: description` against the
  allowed Conventional Commits types; rejects with the expected format plus
  an example on failure; skips merge commits.
- `pre-push` — blocks direct pushes where the local branch is the default
  branch (detected via `git symbolic-ref` / `gh repo view`), enforcing
  "no direct pushes to main" locally. Real GitHub branch-protection
  *settings* are a separate, admin-level, shared-infrastructure change —
  out of scope for this skill to flip silently; this only adds local
  enforcement.

**Docs generated**:
- `AGENTS.md` — four rules: Conventional Commits format; semver-bump
  discipline (version derived from commits via the `semver-release` script,
  never hand-edited, tags are the source of truth); changelog-first
  workflow (every user-facing change needs an `[Unreleased]` entry in the
  same commit/PR); no-direct-push-to-main policy. Written generically,
  substituting the actual default branch name if it isn't `main`.
- `CLAUDE.md` — created as a one-line `@AGENTS.md` import if missing; if one
  already exists, the import line is prepended rather than overwriting
  existing content.

## 5. Skill: `semver-release` (renamed/extended from `changelog-releases-assistant`)

**Keeps unchanged**: the "detect existing automation first" check,
`scripts/extract_changelog.py`, `.github/workflows/release.yml` — this part
already works (proven in this repo's own `v0.1.0` release) and is untouched
apart from the directory rename.

**Adds**: `scripts/suggest_version_bump.py` — inspects commits since the
last `v*.*.*` tag, classifies each by Conventional Commit type/
`BREAKING CHANGE` footer, and computes the correct bump (major > minor >
patch), printing its reasoning.

**Flow when invoked** ("cut a release" / "what's the next version"):
1. Run the bump-suggestion script, show the result to the user.
2. User confirms or overrides the version.
3. On confirmation: update `CHANGELOG.md` (rename `[Unreleased]` →
   `[X.Y.Z] — date`, add a fresh empty `[Unreleased]` above), commit that
   (`chore(release): vX.Y.Z`), create and push the tag — which triggers the
   existing `release.yml` unchanged.

This is "agent-assisted, human-confirmed": the tag/push (hard to reverse,
visible to others) only happens after explicit confirmation, never
automatically.

## 6. Migration mechanics (this repo + marketplace)

**In the `whiting` repo**:
- `gh repo rename whiting`.
- `skills/changelog-releases-assistant/` → split into `skills/inspect/`,
  `skills/repo-init/`, `skills/commit-conventions/`, `skills/semver-release/`.
- `scripts/extract_changelog.py` stays; add `scripts/suggest_version_bump.py`,
  `scripts/hooks/commit-msg`, `scripts/hooks/pre-push`.
- `plugin.json`, `README.md` updated for the new name/scope; new
  `CHANGELOG.md [Unreleased]` entry describing the expansion, released as
  `v0.2.0` once `semver-release` exists (dogfooding — this repo cuts its
  own next release using its own new bump script).
- This repo adopts its own conventions via `commit-conventions`, so its own
  commits/PRs are governed by the same rules it ships to others.

**In `lux-solari-plugins`**: the `changelog-releases-assistant` entry
already exists in `marketplace.json` (confirmed after fast-forwarding a
stale local clone — it was not missing, as initially misreported). This is
a **rename** of that existing entry's `name`, `description`, `homepage`,
`repository`, and `source.repo` fields to `whiting`/the renamed GitHub repo,
plus an update to `README.md`'s install instructions. The `sage-instructor`
and `three-axes-framework` entries are untouched.

## 7. Testing / verification

- `commit-msg` hook: conforming vs. non-conforming message → accept/reject.
- `pre-push` hook: direct push to default branch blocked; branch push
  unaffected.
- `suggest_version_bump.py`: unit-test against a fixture of commit messages
  (feat/fix/breaking), assert the computed bump level.
- `inspect`: run against this repo itself (already has some of these files)
  and against a fresh scratch repo, confirm the report is accurate in both.
- `extract_changelog.py`/`release.yml`: already proven working (this
  session's `v0.1.0` release) — no new testing needed beyond the directory
  move.
- Full dry run on a scratch repo: `inspect` → `repo-init` →
  `commit-conventions` → `semver-release` end-to-end, confirming a rejected
  commit → fixed → accepted → bump suggested → changelog updated → tag
  pushed → release published.

## Decisions log

| Question | Decision |
| --- | --- |
| Plugin name | `whiting` (Charlie Whiting, F1 Race Director — rule enforcement pun, continuing the `hannah` convention) |
| Init scope | Both from-scratch and existing repos |
| Commit enforcement | Local git hook (`commit-msg`), no CI/Node dependency |
| Semver automation | Agent-assisted, human-confirmed (script suggests, user confirms before tag/push) |
| Skill structure | Multiple focused skills, split by lifecycle stage (not by artifact type) |
| CLAUDE.md/AGENTS.md rules | Conventional Commits format, semver-bump discipline, changelog-first workflow, no direct pushes to main |
| CLAUDE.md vs AGENTS.md | CLAUDE.md imports AGENTS.md via `@AGENTS.md`, single source of truth |
| Rename approach | Clean break, no alias (only `v0.1.0` shipped) |
| Marketplace update | In scope; corrected mid-design to a rename of an existing entry, not an addition |
| GitHub repo rename | Yes, rename to `luxsolari/whiting` |
| Existing-repo retrofit | Added `inspect` skill: diagnostic + handoff plan only, no direct writes |
