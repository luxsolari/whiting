#!/bin/sh
set -eu

hook="$(cd "$(dirname "$0")/.." && pwd)/scripts/hooks/commit-msg"
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

fail=0

assert_pass() {
    printf '%s\n' "$1" > "$tmp"
    if ! "$hook" "$tmp" >/dev/null 2>&1; then
        echo "FAIL (expected pass): $1"
        fail=1
    fi
}

assert_fail() {
    printf '%s\n' "$1" > "$tmp"
    if "$hook" "$tmp" >/dev/null 2>&1; then
        echo "FAIL (expected reject): $1"
        fail=1
    fi
}

assert_pass "feat(api): add pagination to /users endpoint"
assert_pass "fix: correct off-by-one in paginator"
assert_pass "chore!: drop support for node 16"
assert_pass "Merge branch 'main' into feature"

assert_fail "added pagination"
assert_fail "Feat: wrong case"
assert_fail "fix:missing space"

if [ "$fail" -eq 0 ]; then
    echo "All commit-msg hook tests passed."
else
    exit 1
fi
