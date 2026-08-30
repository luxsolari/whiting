#!/usr/bin/env python3
"""Merge whiting's AGENTS.md rules into an existing AGENTS.md.

Existing content is never rewritten: sections the file already has are
left exactly as they are, and only the `## ` sections it is missing get
appended, in template order.

Usage:
    merge_agents_md.py <existing-file> <template-file>            # merged doc to stdout
    merge_agents_md.py <existing-file> <template-file> --report   # what would change
"""
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
# Headings are matched on their first few normalized words, so a section
# whose title embeds a repo-specific value ("No direct pushes to main" vs
# "... to develop") still counts as already present.
KEY_WORDS = 4


def heading_key(heading):
    words = re.sub(r"[^a-z0-9]+", " ", heading.lower()).split()
    return " ".join(words[:KEY_WORDS])


def split_sections(text):
    """Return (preamble, [(heading, section_text), ...])."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return text, []
    preamble = text[: matches[0].start()]
    sections = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((match.group(1), text[match.start() : end]))
    return preamble, sections


def missing_sections(existing_text, template_text):
    """Template sections absent from the existing document, in template order."""
    _, existing = split_sections(existing_text)
    have = {heading_key(h) for h, _ in existing}
    _, template = split_sections(template_text)
    return [(h, body) for h, body in template if heading_key(h) not in have]


def merge(existing_text, template_text):
    to_add = missing_sections(existing_text, template_text)
    if not to_add:
        return existing_text
    merged = existing_text.rstrip("\n") + "\n\n"
    merged += "\n".join(body.strip("\n") + "\n" for _, body in to_add)
    return merged


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 2 or flags - {"--report"}:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    existing_text = Path(args[0]).read_text(encoding="utf-8")
    template_text = Path(args[1]).read_text(encoding="utf-8")

    if "--report" in flags:
        to_add = missing_sections(existing_text, template_text)
        added = {heading_key(h) for h, _ in to_add}
        for heading, _ in split_sections(template_text)[1]:
            state = "missing" if heading_key(heading) in added else "present"
            print(f"{state}: {heading}")
        return 0

    print(merge(existing_text, template_text), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
