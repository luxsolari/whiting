# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[0.1.0]: https://github.com/luxsolari/changelog-releases-assistant/releases/tag/v0.1.0
