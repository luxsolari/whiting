#!/usr/bin/env python3
"""Suggest the next semver bump from Conventional Commits since the last tag."""
import re

COMMIT_TYPE_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$"
)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)


def classify_bump(commit_subjects, commit_bodies=None):
    """Classify the required semver bump from commit subject lines.

    commit_bodies, if given, is a list of full commit message bodies
    aligned with commit_subjects, checked for a 'BREAKING CHANGE:' footer.
    """
    bodies = commit_bodies or [""] * len(commit_subjects)
    level = "none"
    for subject, body in zip(commit_subjects, bodies):
        match = COMMIT_TYPE_RE.match(subject)
        if not match:
            continue
        if match.group("breaking") or BREAKING_FOOTER_RE.search(body):
            return "major"
        commit_type = match.group("type")
        if commit_type == "feat" and level != "major":
            level = "minor"
        elif commit_type == "fix" and level not in ("major", "minor"):
            level = "patch"
    return level


def next_version(current, bump):
    """Compute the next version string from a 'vX.Y.Z' tag and a bump level."""
    major, minor, patch = (int(part) for part in current.lstrip("v").split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    if bump == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    raise ValueError(f"No release needed: bump={bump!r}")
