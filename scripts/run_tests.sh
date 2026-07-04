#!/bin/sh
# Runs every test in tests/: python unittest files and POSIX shell test scripts.
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

for test_file in "$root"/tests/test_*.py; do
    [ -e "$test_file" ] || continue
    echo "== $test_file =="
    python3 "$test_file" || fail=1
done

for test_file in "$root"/tests/test_*.sh; do
    [ -e "$test_file" ] || continue
    echo "== $test_file =="
    sh "$test_file" || fail=1
done

if [ "$fail" -eq 0 ]; then
    echo "All tests passed."
else
    echo "Some tests failed." >&2
fi
exit "$fail"
