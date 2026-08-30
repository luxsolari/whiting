# Bitácora

Work log for this repo. Newest entry first. Read it before starting work;
append to it after finishing a task.

Each entry records: what changed, what was verified and how, what is still
open, what was ruled out and why, and the files that matter. Past ~40
entries, fold all but the most recent 15 into a historical summary, one
line each — never dropping a decision or a recorded failure.

---

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
  Nothing automates that file — `semver-release` doesn't touch it — so it
  will drift again at the next release unless the skill starts bumping it.)
- **Ruled out**: an interactive three-way merge for existing `AGENTS.md`
  files — heading-level section matching (first four normalized words, so
  "No direct pushes to develop" matches the template's "…to main") is
  predictable and never rewrites a line the repo already had. Near-duplicate
  sections under unrecognised headings are surfaced to the user instead of
  auto-reconciled.
- **Files**: `templates/AGENTS.md.tmpl`, `templates/BITACORA.md.tmpl`,
  `scripts/merge_agents_md.py`, `skills/repo-init/SKILL.md`,
  `skills/commit-conventions/SKILL.md`, `skills/inspect/SKILL.md`,
  `scripts/inspect_repo.sh`, `tests/`.
