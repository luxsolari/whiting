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
rm -rf "$workdir"

if [ "$fail" -eq 0 ]; then
    echo "All inspect_repo.sh tests passed."
else
    exit 1
fi
