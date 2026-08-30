#!/bin/sh
set -eu

script="$(cd "$(dirname "$0")/.." && pwd)/scripts/inspect_repo.sh"
fail=0

# Case 1: not a git repo at all
workdir=$(mktemp -d)
out=$(cd "$workdir" && "$script" 2>&1) && rc=0 || rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: expected exit 1 for non-git directory"; fail=1; }
printf '%s\n' "$out" | grep -q "not a git repository" || { echo "FAIL: missing 'not a git repository' message"; fail=1; }
rm -rf "$workdir"

# Case 2: minimal repo, no LICENSE/README/CHANGELOG
workdir=$(mktemp -d)
(cd "$workdir" && git init -q && git config user.email t@example.com && git config user.name Test && git commit -q --allow-empty -m "chore: init")
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "LICENSE missing" || { echo "FAIL: expected LICENSE missing warning"; fail=1; }
printf '%s\n' "$out" | grep -q "CHANGELOG.md missing" || { echo "FAIL: expected CHANGELOG.md missing warning"; fail=1; }
rm -rf "$workdir"

# Case 3: fully compliant repo
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    touch LICENSE
    printf '# demo\n\n[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)\n' > README.md
    printf '# Changelog\n\n## [0.1.0] - 2026-01-01\n' > CHANGELOG.md
    printf '# Agent Rules\n\n## Register\n\n## Answer scope\n\n## Disagreement\n\n## Language\n\n## Work log\n' > AGENTS.md
    printf '@AGENTS.md\n' > CLAUDE.md
    printf '# Bitacora\n' > BITACORA.md
    mkdir -p scripts/hooks
    git config whiting.defaultbranch main
    git config core.hooksPath scripts/hooks
    git add -A
    git commit -q -m "feat: initial commit"
    git tag v0.1.0
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "LICENSE present" || { echo "FAIL: expected LICENSE present"; fail=1; }
printf '%s\n' "$out" | grep -q "CHANGELOG.md present and Keep a Changelog-formatted" || { echo "FAIL: expected CHANGELOG ok"; fail=1; }
printf '%s\n' "$out" | grep -q 'tags follow v\*\.\*\.\* scheme' || { echo "FAIL: expected tag scheme ok"; fail=1; }
printf '%s\n' "$out" | grep -q "core.hooksPath set to scripts/hooks" || { echo "FAIL: expected hooksPath ok"; fail=1; }
printf '%s\n' "$out" | grep -q "README.md has shields.io badges" || { echo "FAIL: expected badge check ok"; fail=1; }
printf '%s\n' "$out" | grep -q "AGENTS.md present and CLAUDE.md imports it" || { echo "FAIL: expected AGENTS/CLAUDE ok"; fail=1; }
printf '%s\n' "$out" | grep -q "AGENTS.md covers the working-agreement defaults" || { echo "FAIL: expected working-agreement sections ok"; fail=1; }
printf '%s\n' "$out" | grep -q "BITACORA.md work log present" || { echo "FAIL: expected BITACORA present"; fail=1; }
rm -rf "$workdir"

# Case 4: AGENTS.md with only the release rules -> flags the missing defaults
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    printf '# Agent Rules\n\n## Conventional Commits\n' > AGENTS.md
    printf '@AGENTS.md\n' > CLAUDE.md
    git add -A
    git commit -q -m "chore: init"
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "AGENTS.md missing working-agreement sections" || { echo "FAIL: expected missing working-agreement warning"; fail=1; }
printf '%s\n' "$out" | grep -q "BITACORA.md missing" || { echo "FAIL: expected BITACORA missing warning"; fail=1; }
rm -rf "$workdir"

# Case 5: manifest version drifted from the last tag
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    mkdir -p .claude-plugin
    printf '{\n  "name": "demo",\n  "version": "0.2.0"\n}\n' > .claude-plugin/plugin.json
    git add -A
    git commit -q -m "chore: init"
    git tag v0.3.0
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "says version 0.2.0 but the last tag is v0.3.0" || { echo "FAIL: expected manifest drift warning"; fail=1; }
rm -rf "$workdir"

# Case 6: manifest version matches the last tag, and an untagged repo is silent
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    printf '{\n  "name": "demo",\n  "version": "0.3.0"\n}\n' > package.json
    git add -A
    git commit -q -m "chore: init"
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "version 0.3.0 matches the last tag" && { echo "FAIL: untagged repo should not report a manifest match"; fail=1; }
printf '%s\n' "$out" | grep -q "package.json says version" && { echo "FAIL: untagged repo should not warn about drift"; fail=1; }
(cd "$workdir" && git tag v0.3.0)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "package.json version 0.3.0 matches the last tag v0.3.0" || { echo "FAIL: expected manifest match"; fail=1; }
rm -rf "$workdir"

# Case 7: a version nested under dependencies is not the manifest's own
workdir=$(mktemp -d)
(
    cd "$workdir"
    git init -q
    git config user.email t@example.com
    git config user.name Test
    printf '{\n  "dependencies": {\n    "left-pad": {\n      "version": "9.9.9"\n    }\n  },\n  "version": "0.3.0"\n}\n' > package.json
    git add -A
    git commit -q -m "chore: init"
    git tag v0.3.0
)
out=$(cd "$workdir" && "$script") || true
printf '%s\n' "$out" | grep -q "package.json version 0.3.0 matches the last tag v0.3.0" || { echo "FAIL: expected the manifest's own version, not a dependency's"; fail=1; }
rm -rf "$workdir"

if [ "$fail" -eq 0 ]; then
    echo "All inspect_repo.sh tests passed."
else
    exit 1
fi
