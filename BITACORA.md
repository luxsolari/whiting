# Bitácora

Work log for this repo. Newest entry first. Read it before starting work;
append to it after finishing a task.

Each entry records: what changed, what was verified and how, what is still
open, what was ruled out and why, and the files that matter. Past ~40
entries, fold all but the most recent 15 into a historical summary, one
line each — never dropping a decision or a recorded failure.

---

## 2026-08-30 — release v0.5.0 prepared; step ordering corrected

- **Changed**: `CHANGELOG.md`'s `## [Unreleased]` renamed to
  `## [0.5.0] — 2026-08-30` with a fresh `## [Unreleased]` and a `[0.5.0]`
  link; `.claude-plugin/plugin.json` `0.4.0` → `0.5.0`. Also moved the
  `claude plugin tag --dry-run` step from 4 to 6 in
  `skills/semver-release/SKILL.md`.
- **Verified**: `suggest_version_bump.py` reads two commits since `v0.4.0`,
  one a `feat:`, and suggests `v0.5.0`; pre-flight manifest check passed
  (`plugin.json` 0.4.0 = tag v0.4.0).
- **Recorded failure (found by using it)**: the step as shipped in #11 said
  to run the check *before* committing. It refuses on a dirty tree —
  `× Uncommitted changes affecting this release — commit them first so the
  tag points at the version you intend to release` — so it can only run
  after the release commit exists. Caught on the very first real use, one
  release after being written. The lesson is the obvious one: a command
  written into a skill from `--help` output alone is not verified; run it
  in the position the skill puts it in.
- **Open**: the tag, once this lands (see the v0.4.0 entry for why the
  push has to go through `release.yml`'s `workflow_dispatch`).
- **Files**: `CHANGELOG.md`, `.claude-plugin/plugin.json`,
  `skills/semver-release/SKILL.md`.

## 2026-08-30 — semver-release checks the plugin/marketplace version pair

- **Changed**: `skills/semver-release/SKILL.md` step 4 now runs
  `claude plugin tag --dry-run <path>` in plugin repos, and the pre-flight
  check points at it for the marketplace half of the drift.
- **Verified**: ran the command for real, not from memory. Against this
  repo it prints `Version: 0.4.0 (from plugin.json)` / `Tag:
  whiting--v0.4.0` and exits 0. Against a scratch marketplace fixture
  whose `plugin.json` said `0.2.0` and whose `marketplace.json` entry said
  `0.1.0`, it exits 1 with `× Version mismatch: ... plugin.json wins at
  install time`.
- **Open**: nothing.
- **Ruled out**: dropping `--dry-run`. The command creates
  `{name}--v{version}` tags (`whiting--v0.4.0`), a different scheme from
  the `v*.*.*` tags `release.yml` triggers on — using it to cut releases
  would silently stop publishing them. It is a validator here, nothing
  more. Also not ported to the Codex copy of this skill: `claude plugin`
  is Claude Code's CLI, and that repo validates with its own
  `scripts/validate_plugin.py`.
- **Context**: found because the Claude marketplace card still showed
  whiting at `0.2.0`. That turned out to be a stale local cache
  (`claude plugin marketplace update lux-solari-plugins`), not a bad
  manifest — the marketplace entry pins no version and reads `plugin.json`
  from the default branch, which is `0.4.0`.
- **Files**: `skills/semver-release/SKILL.md`, `CHANGELOG.md`.

## 2026-08-30 — v0.4.0 released; Codex port brought to parity

- **Changed**: nothing in this repo beyond this log. `v0.4.0` is tagged at
  `fcb60c9` and its GitHub Release is published from the `## [0.4.0]`
  changelog section. The Codex port in `luxsolari/lux-solari-codex-plugins`
  now carries the same runtime (`merge_agents_md.py`,
  `manifest_version.py`, the `AGENTS.md`/`BITACORA.md` templates, the
  drift check), adapted for that host.
- **Verified**: `git ls-remote --tags` shows `v0.4.0` → `fcb60c9`; the
  Release body matches `extract_changelog.py v0.4.0`. The Codex repo's
  full CI command list ran green locally and on both `validate` runs.
- **Open**: nothing.
- **Ruled out / recorded failure**: **pushing a tag from a Claude Code
  remote session does not work.** `git push origin refs/tags/v0.4.0`
  fails with `send-pack: unexpected disconnect while reading sideband
  packet` on every attempt (five, with backoff) — the sandbox's git write
  mediation allows branch refs and refuses tag refs. Branch pushes to the
  same remote succeed, so it is not a network flake and retrying is
  wasted effort. The working path is the one `semver-release` already
  documents for backfills: dispatch `release.yml` on the default branch
  with `tag=vX.Y.Z`, and its `gh release create` creates the tag at that
  branch's HEAD and publishes the Release in one step. Use that from a
  remote session; a local clone can still push the tag directly.
- **Codex-port adaptations worth remembering**: `$CLAUDE_PLUGIN_ROOT` →
  `<plugin root>` (enforced by that repo's `test_host_portability.py`),
  `.codex-plugin/plugin.json` checked ahead of the Claude and language
  manifests, and the Three Axes note links the framework repo instead of
  citing a slash command Codex does not have.
- **Files**: `BITACORA.md` here; `plugins/whiting/**`,
  `docs/parity-ledger.md`, `docs/parity-inventory.md` there.

## 2026-08-30 — release v0.4.0 prepared

- **Changed**: `CHANGELOG.md`'s `## [Unreleased]` renamed to
  `## [0.4.0] — 2026-08-30` with a fresh empty `## [Unreleased]` above it
  and a `[0.4.0]` reference link added; `.claude-plugin/plugin.json`
  bumped `0.3.0` → `0.4.0` in the same commit, which is `semver-release`'s
  new step 4 running for the first time. Also tidied a stray blank line
  that split the `### Changed` list.
- **Verified**: `suggest_version_bump.py` reads one `feat:` commit since
  `v0.3.0` and suggests `v0.4.0`; `extract_changelog.py v0.4.0` returns
  the full section, so the release workflow has a body to publish.
  Pre-flight manifest check passed before the bump (`plugin.json` 0.3.0 =
  tag v0.3.0).
- **Open**: nothing. The tag exists at `fcb60c9` and the Release is
  published; see the entry above for how it was created.
- **Ruled out**: tagging from the branch. The workflow reads
  `CHANGELOG.md` at the tagged commit, and a tag on an unmerged branch
  would publish a release pointing at history that isn't on `main`.
- **Files**: `CHANGELOG.md`, `.claude-plugin/plugin.json`.

## 2026-08-30 — agent rule files: working-agreement defaults + merge-not-replace

- **Changed**: `templates/AGENTS.md.tmpl` now carries the working-agreement
  defaults (register, answer scope, disagreement, language, work log, and a
  closing note on the three-axes-framework plugin) on top of the release
  rules. Added `templates/BITACORA.md.tmpl` and
  `scripts/merge_agents_md.py`, which appends only the sections an existing
  `AGENTS.md` is missing. `repo-init` now creates `AGENTS.md`, `CLAUDE.md`
  and `BITACORA.md` as part of the baseline; `commit-conventions` still owns
  the merge procedure; `inspect` flags a missing `BITACORA.md` and any
  missing working-agreement section.
- **Verified**: `scripts/run_tests.sh` green, including new
  `tests/test_merge_agents_md.py` (6 cases) and the new inspect case for a
  repo whose `AGENTS.md` only has release rules. This repo's own
  `AGENTS.md` was regenerated from the template and re-checked with
  `merge_agents_md.py --report` — all sections present.
- **Open**: nothing. (`.claude-plugin/plugin.json` said `0.2.0` while the
  last release was `0.3.0`; corrected to `0.3.0` in this same branch.
  Root cause: nothing wrote it. `semver-release` now sets manifest
  versions in the release commit and checks the manifest against the last
  tag before cutting a release, and `inspect` flags the drift in repos
  that never cut a release through the skill, so it should not drift
  again.)
- **Ruled out**: an interactive three-way merge for existing `AGENTS.md`
  files — heading-level section matching (first four normalized words, so
  "No direct pushes to develop" matches the template's "…to main") is
  predictable and never rewrites a line the repo already had. Near-duplicate
  sections under unrecognised headings are surfaced to the user instead of
  auto-reconciled.
- **Note**: `inspect`'s manifest check parses via
  `scripts/manifest_version.py` rather than `sed` — the first `"version"`
  key in a JSON file is not reliably the manifest's own. TOML uses
  `tomllib` where available, falling back to a regex scoped to `[project]`
  / `[tool.poetry]`.
- **Files**: `templates/AGENTS.md.tmpl`, `templates/BITACORA.md.tmpl`,
  `scripts/merge_agents_md.py`, `skills/repo-init/SKILL.md`,
  `skills/commit-conventions/SKILL.md`, `skills/inspect/SKILL.md`,
  `scripts/inspect_repo.sh`, `tests/`.
