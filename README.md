# Whiting

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code plugin that bootstraps a repo's whole release discipline:
init the repo, enforce Conventional Commits, derive semver bumps from
commit history, and publish GitHub Releases straight from `CHANGELOG.md`.
Named after Charlie Whiting, F1's longtime Race Director — famous for
strictly enforcing the rulebook.

## What it does

Four focused skills, one per lifecycle stage:

- **`inspect`** — audits an existing repo against these conventions
  (changelog format, tag scheme, existing automation, commit style,
  hook activation, AGENTS.md/CLAUDE.md, branch protection) and reports a
  concrete remediation plan. Read-only, never writes.
- **`repo-init`** — bootstraps the baseline: `git init` if needed,
  `LICENSE`, `README.md`, and a Keep a Changelog `CHANGELOG.md`.
- **`commit-conventions`** — installs a `commit-msg` hook (Conventional
  Commits) and a `pre-push` hook (blocks direct pushes to the default
  branch), and generates `AGENTS.md` (the rules) with `CLAUDE.md`
  importing it.
- **`semver-release`** — suggests the next version from commits since the
  last tag, and publishes a GitHub Release from the matching
  `CHANGELOG.md` section whenever that tag is pushed.

## Requirements

- A repo with (or being bootstrapped to have) a `CHANGELOG.md` following
  [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and tags in
  `v*.*.*` form. `inspect` and `repo-init` help you get there.
- `gh` CLI, authenticated, for anything that touches GitHub (Releases,
  reading the default branch, license text lookup).

## Install

```
/plugin marketplace add luxsolari/lux-solari-plugins
/plugin install whiting@lux-solari-plugins
```

Then, in any repo:

```
Audit this repo against whiting's conventions.
```

or, starting fresh:

```
Bootstrap this repo with whiting.
```

## This repo dogfoods itself

`scripts/`, `.github/workflows/release.yml`, `AGENTS.md`, and `CLAUDE.md`
here are exactly what the skills above install elsewhere — including this
repo's own commit-msg/pre-push hooks and its own releases.

## License

MIT — see [LICENSE](LICENSE).
