---
name: semver-release
description: >-
  Wire a repo's CHANGELOG.md up to its GitHub Releases, and suggest the
  next semver bump from Conventional Commits since the last tag. Use when
  the user wants to populate an empty GitHub Releases tab, backfill
  releases for existing tags, automate publishing a Release on every
  version tag push, or figure out what the next version number should be.
  Applies to any repo following Keep a Changelog conventions and tagging
  releases with a "v*.*.*" scheme.
license: MIT
---

# semver-release

Wires a repo's `CHANGELOG.md` up to its GitHub Releases: pushing a version
tag publishes a Release whose body is that version's changelog section,
verbatim. Also suggests the next version number from Conventional Commits
since the last tag, so version bumps aren't guessed by hand.

## When to use this skill

- "Populate the GitHub Releases tab for this repo."
- "Set up automatic releases from the changelog."
- "Backfill GitHub releases for our existing tags."
- "What should the next version be?" / "Cut a release."

## Before touching anything

1. **Check for an existing release workflow.** Grep `.github/workflows/*.yml`
   for `gh release`, `softprops/action-gh-release`, `actions/create-release`,
   or similar. If one exists, stop and tell the user what's already there
   instead of adding a second, competing workflow.
2. **Check `CHANGELOG.md` follows Keep a Changelog conventions**: version
   sections headed `## [X.Y.Z] — YYYY-MM-DD` (a regex on `^## \[VERSION\]`
   must match). If there's no changelog, or its format doesn't match, this
   skill needs `repo-init` run first — don't guess a format.
3. **Check the tag scheme**: `git tag -l` should show tags like `v0.1.0`.
   If tags use a different prefix or omit `v`, this skill's workflow's
   `on.push.tags` glob, `scripts/extract_changelog.py`, and
   `scripts/suggest_version_bump.py`'s `v`-prefix handling all need the
   same adjustment — don't fix one and silently leave the others broken.

## Installing release automation

Copy these files, unmodified unless step 3 above required a tag-scheme
tweak — applied consistently across all three:

| Source (`$CLAUDE_PLUGIN_ROOT/...`) | Destination |
| --- | --- |
| `scripts/extract_changelog.py` | `scripts/extract_changelog.py` |
| `scripts/suggest_version_bump.py` | `scripts/suggest_version_bump.py` |
| `.github/workflows/release.yml` | `.github/workflows/release.yml` |

`extract_changelog.py` takes a version (`v0.7.3` or `0.7.3`) and prints
the matching `## [X.Y.Z]` section of `CHANGELOG.md`, stripping the
trailing `[X.Y.Z]: https://...` reference link and any `---` separator.
The workflow runs on every `v*.*.*` tag push (and via `workflow_dispatch`
with a `tag` input for backfilling), pipes that script's output into
`gh release create` (or `gh release edit` if a release for that tag
already exists), and needs no secrets beyond the default `GITHUB_TOKEN`
(`permissions: contents: write`).

## Cutting a release

1. Run the bump suggester from the repo root:
   ```
   python3 scripts/suggest_version_bump.py
   ```
   It prints the last tag, how many commits were considered, the
   classified bump level (feat → minor, fix → patch, `!`/`BREAKING
   CHANGE:` → major), and the suggested next version.
2. Show the user the suggestion and ask them to confirm or override it —
   never tag/push without explicit confirmation; this is a hard-to-reverse,
   externally-visible action.
3. On confirmation: in `CHANGELOG.md`, rename `## [Unreleased]` to
   `## [X.Y.Z] — YYYY-MM-DD` (today's date) and add a fresh empty
   `## [Unreleased]` above it.
4. Commit that: `git commit -m "chore(release): vX.Y.Z"`.
5. Land the commit per this repo's normal rules (branch + PR if
   `commit-conventions` is installed — don't push the release commit
   straight to the default branch either).
6. After the release commit reaches the default branch, tag it and push
   the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`. This triggers the
   installed workflow, which publishes the GitHub Release.

## Backfilling existing tags

For tags that predate this skill and have no Release yet, dispatch the
workflow once per tag: ref = default branch, input `tag=v0.x.y`.

## Scope notes

- No secrets needed beyond the default `GITHUB_TOKEN`.
- Every installed file is generic: no repo name, owner, or path is
  hardcoded, so the same files work unmodified across repos (beyond the
  tag-scheme check above).
