# Whiting

[![Version](https://img.shields.io/github/v/release/luxsolari/whiting)](https://github.com/luxsolari/whiting/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code plugin that bootstraps a repo's whole release discipline:
init the repo, enforce Conventional Commits, derive semver bumps from
commit history, and publish GitHub Releases straight from `CHANGELOG.md`.

Whiting is named after *[Charlie Whiting](https://en.wikipedia.org/wiki/Charlie_Whiting)*,
the FIA's Race Director and Safety Delegate from 1997 until his death in
2019 — the steward at the foot of every grid who enforced the rulebook
race after race, and whose tenure was shaped by
[the fatal 1994 San Marino Grand Prix weekend](https://en.wikipedia.org/wiki/1994_San_Marino_Grand_Prix),
after which he helped drive the FIA's push for the stricter technical and
safety regulations that still govern the sport today. This tool does the
same for your repo: it enforces the rules — commit format, versioning,
changelog discipline — so releases stop depending on anyone remembering
to follow them by hand.

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
