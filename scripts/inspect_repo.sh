#!/bin/sh
# Audits a repo against whiting's conventions. Read-only, makes no changes.
set -u

pass=0
warn=0
fail=0

report_ok() { printf '✅ %s\n' "$1"; pass=$((pass + 1)); }
report_warn() { printf '⚠️  %s\n' "$1"; warn=$((warn + 1)); }
report_fail() { printf '❌ %s\n' "$1"; fail=$((fail + 1)); }

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    report_ok "git repository present"
else
    report_fail "not a git repository"
    printf '\n%d ok, %d warnings, %d failed\n' "$pass" "$warn" "$fail"
    exit 1
fi

default_branch=$(git config --get whiting.defaultbranch || true)
if [ -z "$default_branch" ]; then
    default_branch=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)
fi
default_branch=${default_branch:-main}
report_ok "default branch resolved as '$default_branch'"

[ -f LICENSE ] && report_ok "LICENSE present" || report_warn "LICENSE missing"
[ -f README.md ] && report_ok "README.md present" || report_warn "README.md missing"

if [ -f CHANGELOG.md ]; then
    if grep -qE '^## \[[^]]+\]' CHANGELOG.md; then
        report_ok "CHANGELOG.md present and Keep a Changelog-formatted"
    else
        report_warn "CHANGELOG.md present but no '## [X.Y.Z]' section found"
    fi
else
    report_warn "CHANGELOG.md missing"
fi

tag_sample=$(git tag -l | head -n 5)
if [ -z "$tag_sample" ]; then
    report_warn "no git tags found"
elif printf '%s\n' "$tag_sample" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    report_ok "tags follow v*.*.* scheme"
else
    report_warn "tags exist but don't match v*.*.* (found: $(printf '%s' "$tag_sample" | head -n1))"
fi

# Manifest version vs. the last tag: a mismatch means a release commit
# renamed the changelog but never wrote the version back into the manifest.
# manifest_version.py reads only the manifest's own version, so a `version`
# nested under dependencies can't be mistaken for it.
last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for manifest in .claude-plugin/plugin.json package.json pyproject.toml; do
    [ -f "$manifest" ] || continue
    # No tags yet is the normal state for a fresh repo — nothing to compare.
    [ -n "$last_tag" ] || continue
    if ! command -v python3 >/dev/null 2>&1; then
        report_warn "python3 not available — skipped the $manifest version check"
        continue
    fi
    declared=$(python3 "$script_dir/manifest_version.py" "$manifest" 2>/dev/null || true)
    if [ -z "$declared" ]; then
        report_warn "$manifest declares no version of its own (or isn't parseable)"
    elif [ "$declared" = "${last_tag#v}" ]; then
        report_ok "$manifest version $declared matches the last tag $last_tag"
    else
        report_warn "$manifest says version $declared but the last tag is $last_tag (a release skipped the manifest bump)"
    fi
done

if [ -d .github/workflows ] && grep -rl -E 'gh release|softprops/action-gh-release|actions/create-release' .github/workflows 2>/dev/null | grep -q .; then
    report_warn "existing release-publishing workflow found — check before adding another"
else
    report_ok "no competing release-publishing workflow found"
fi

hooks_path=$(git config --get core.hooksPath || true)
if [ "$hooks_path" = "scripts/hooks" ]; then
    report_ok "core.hooksPath set to scripts/hooks"
else
    report_warn "core.hooksPath not set to scripts/hooks (commit-msg/pre-push hooks inactive)"
fi

recent_subjects=$(git log -20 --format=%s 2>/dev/null || true)
if [ -n "$recent_subjects" ]; then
    total=$(printf '%s\n' "$recent_subjects" | wc -l | tr -d ' ')
    conventional=$(printf '%s\n' "$recent_subjects" | grep -cE '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+' || true)
    report_ok "commit style: $conventional/$total of last $total commits already follow Conventional Commits"
else
    report_warn "no commit history to sample"
fi

if [ -f AGENTS.md ]; then
    if [ -f CLAUDE.md ] && grep -q '@AGENTS.md' CLAUDE.md; then
        report_ok "AGENTS.md present and CLAUDE.md imports it"
    else
        report_warn "AGENTS.md present but CLAUDE.md doesn't import it"
    fi

    missing_sections=""
    for section in Register "Answer scope" Disagreement Language "Work log"; do
        grep -qi "^## $section" AGENTS.md || missing_sections="$missing_sections, $section"
    done
    if [ -z "$missing_sections" ]; then
        report_ok "AGENTS.md covers the working-agreement defaults"
    else
        report_warn "AGENTS.md missing working-agreement sections:${missing_sections#,}"
    fi
else
    report_warn "AGENTS.md missing"
fi

if [ -f BITACORA.md ]; then
    report_ok "BITACORA.md work log present"
else
    report_warn "BITACORA.md missing (AGENTS.md's work-log rule has nothing to append to)"
fi

if [ -f README.md ]; then
    if grep -q 'img\.shields\.io' README.md; then
        report_ok "README.md has shields.io badges"
    else
        report_warn "README.md has no shields.io badges"
    fi
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    origin_url=$(git config --get remote.origin.url || true)
    repo_slug=$(printf '%s' "$origin_url" | sed -E 's#.*[:/]([^/]+/[^/]+)(\.git)?$#\1#')

    if [ -n "$repo_slug" ] && gh api "repos/$repo_slug/branches/$default_branch/protection" >/dev/null 2>&1; then
        report_ok "GitHub branch protection enabled on '$default_branch'"
    else
        report_warn "GitHub branch protection not detected on '$default_branch' (or gh lacks admin read access)"
    fi

    if [ -n "$repo_slug" ]; then
        description=$(gh repo view "$repo_slug" --json description -q '.description // ""' 2>/dev/null || true)
        if [ -n "$description" ]; then
            report_ok "GitHub repo description set"
        else
            report_warn "GitHub repo description not set"
        fi
        topic_count=$(gh repo view "$repo_slug" --json repositoryTopics -q '.repositoryTopics | length' 2>/dev/null || echo 0)
        if [ "${topic_count:-0}" -gt 0 ]; then
            report_ok "GitHub repo topics set ($topic_count)"
        else
            report_warn "GitHub repo topics not set"
        fi
    else
        report_warn "no origin remote — skipped GitHub description/topics check"
    fi
else
    report_warn "gh not authenticated — skipped branch protection and metadata checks"
fi

printf '\n%d ok, %d warnings, %d failed\n' "$pass" "$warn" "$fail"
[ "$fail" -eq 0 ]
