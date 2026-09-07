# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.6.0] — 2026-09-07

### Changed
- The work log this plugin bootstraps is now `JOURNAL.md` with a `# Journal` heading,
  renamed from `BITACORA.md` / `# Bitácora`. `templates/BITACORA.md.tmpl` became
  `templates/JOURNAL.md.tmpl`; `repo-init`, `inspect`, `commit-conventions`, the rendered
  `AGENTS.md` work-log rule, `scripts/inspect_repo.sh` and this repository's own log and
  working agreement follow.
- `inspect` and `scripts/inspect_repo.sh` now report an existing `BITACORA.md` as needing a
  rename rather than as a missing work log, and `repo-init` renames it instead of rendering
  a second one. A repo with two work logs is worse off than a repo with the old name.

## [0.5.0] — 2026-08-30

### Added
- `semver-release` runs `claude plugin tag --dry-run` in plugin repos,
  right after the release commit, so a `plugin.json` version that
  disagrees with its enclosing `marketplace.json` entry is caught before
  the tag goes out. Skipped where the `claude` CLI isn't available.

## [0.4.0] — 2026-08-30

### Added
- `AGENTS.md` now ships the working-agreement defaults on top of the
  release rules — register, answer scope, disagreement, language, and a
  `BITACORA.md` work log agents read before starting and append to when
  they finish — plus a closing note on the three-axes-framework plugin
  that can be dropped when it isn't in use.
- `repo-init` creates `AGENTS.md`, `CLAUDE.md` (importing it) and
  `BITACORA.md` as part of the baseline, from the new
  `templates/BITACORA.md.tmpl`; they are no longer only a
  `commit-conventions` side effect.
- `scripts/merge_agents_md.py`: merges whiting's rules into an existing
  `AGENTS.md` by appending only the sections it lacks, matching headings
  on their first four normalized words so a repo's own
  "No direct pushes to develop" is not duplicated. `--report` shows what
  would change before anything is written.
- `inspect` reports whether `AGENTS.md` covers the working-agreement
  sections and whether `BITACORA.md` exists, and flags a manifest version
  (`plugin.json`, `package.json`, `pyproject.toml`) that has drifted from
  the last tag.
- `scripts/manifest_version.py`: reads a manifest's own declared version —
  parsing JSON as JSON and TOML with `tomllib` (with a table-scoped regex
  fallback for Python < 3.11), so a `version` nested under `dependencies`
  is never mistaken for it. Used by `inspect`'s drift check.

### Changed
- `commit-conventions` and `repo-init` merge into an existing
  `AGENTS.md`/`CLAUDE.md` instead of asking to overwrite: existing
  content is left exactly as written.
- `semver-release` now sets the version in the repo's manifests
  (`plugin.json`, `package.json`, `pyproject.toml`) as part of the release
  commit, and checks the manifest against the last tag before cutting a new
  release — the step whose absence let this repo's `plugin.json` drift.

### Fixed
- `.claude-plugin/plugin.json` said `0.2.0` while the last release was
  `0.3.0`; the manifest version now matches the tag.

## [0.3.0] — 2026-07-05

### Added
- `repo-init` now renders Version and License shields.io badges into the
  generated `README.md` (new `REPO_SLUG` / `LICENSE_NAME` template
  placeholders) and, when a GitHub remote and `gh` auth are available,
  sets the repo description and topics via `gh repo edit`.
- `inspect` now flags missing README badges (offline) and a missing
  GitHub description or topics (best-effort, gh-gated).
- `scripts/shields_escape.py` escapes the license id for the shields badge, so non-MIT SPDX ids (e.g. `Apache-2.0` → `Apache--2.0`) render correctly; `repo-init` runs it to compute `LICENSE_NAME`.

## [0.2.0] — 2026-07-04

### Added
- `inspect` skill: read-only audit of an existing repo against whiting's conventions (changelog format, tag scheme, existing release automation, commit style, hook activation, AGENTS.md/CLAUDE.md, branch protection), with a concrete remediation plan pointing at `repo-init`, `commit-conventions`, or `semver-release`.
- `repo-init` skill: bootstraps `LICENSE`, `README.md`, and a Keep a Changelog `CHANGELOG.md`, including `git init` for from-scratch repos.
- `commit-conventions` skill: installs a `commit-msg` hook enforcing Conventional Commits and a `pre-push` hook blocking direct pushes to the default branch (both via a tracked `scripts/hooks/` directory activated with `core.hooksPath`), and generates `AGENTS.md` (with `CLAUDE.md` importing it) documenting commit format, semver-bump discipline, changelog-first workflow, and the no-direct-push rule.
- `scripts/suggest_version_bump.py`: classifies commits since the last tag by Conventional Commit type/breaking-change footer and suggests the next semver version.
- `scripts/render_template.py`: generic `{{KEY}}` placeholder substitution used by `repo-init` and `commit-conventions` to render their bundled templates.

### Changed
- Renamed the plugin and its GitHub repo from `changelog-releases-assistant` to **whiting**; `changelog-releases-assistant`'s skill is renamed `semver-release` and extended with the bump-suggestion flow above. Clean-break rename, no compatibility alias.

## [0.1.0] — 2026-07-04

### Added
- Initial release of the **Changelog Releases Assistant** skill: `skills/changelog-releases-assistant/SKILL.md` scaffolds a target repo's GitHub Release automation from its `CHANGELOG.md`.
- `.github/workflows/release.yml`: publishes a GitHub Release whenever a `v*.*.*` tag is pushed, using the matching `CHANGELOG.md` section (`## [X.Y.Z]`) as the release body. Also accepts `workflow_dispatch` with a `tag` input to backfill releases for existing tags.
- `scripts/extract_changelog.py`: extracts a single version's section from a Keep a Changelog-formatted `CHANGELOG.md`, stripping the trailing reference-link line and `---` separator, for use as release notes.
- This repo dogfoods its own automation: the workflow and script above are the exact files the skill copies into target repos.

[0.5.0]: https://github.com/luxsolari/whiting/releases/tag/v0.5.0
[0.4.0]: https://github.com/luxsolari/whiting/releases/tag/v0.4.0
[0.3.0]: https://github.com/luxsolari/whiting/releases/tag/v0.3.0
[0.2.0]: https://github.com/luxsolari/whiting/releases/tag/v0.2.0
[0.1.0]: https://github.com/luxsolari/changelog-releases-assistant/releases/tag/v0.1.0
