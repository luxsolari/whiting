#!/bin/sh
set -eu

hook="$(cd "$(dirname "$0")/.." && pwd)/scripts/hooks/pre-push"
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

cd "$workdir"
git init -q

fail=0

assert_blocked() {
    git config whiting.defaultbranch "$1"
    if printf '%s\n' "$2" | "$hook" origin git@example.com:test.git >/dev/null 2>&1; then
        echo "FAIL (expected block): $2"
        fail=1
    fi
}

assert_allowed() {
    git config whiting.defaultbranch "$1"
    if ! printf '%s\n' "$2" | "$hook" origin git@example.com:test.git >/dev/null 2>&1; then
        echo "FAIL (expected allow): $2"
        fail=1
    fi
}

assert_blocked main "refs/heads/main abc123 refs/heads/main def456"
assert_allowed main "refs/heads/feature abc123 refs/heads/feature def456"
assert_allowed main "HEAD abc123 refs/tags/v1.0.0 def456"
assert_blocked trunk "refs/heads/trunk abc123 refs/heads/trunk def456"

if [ "$fail" -eq 0 ]; then
    echo "All pre-push hook tests passed."
else
    exit 1
fi
