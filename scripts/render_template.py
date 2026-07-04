#!/usr/bin/env python3
"""Render a template by substituting {{KEY}} placeholders."""
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def render(template_text, mapping):
    def replace(match):
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"Missing template value for {{{{{key}}}}}")
        return mapping[key]

    return PLACEHOLDER_RE.sub(replace, template_text)


def main():
    if len(sys.argv) < 2:
        print("Usage: render_template.py <template-file> [KEY=VALUE ...]", file=sys.stderr)
        return 1
    template_path = Path(sys.argv[1])
    # Validate all arguments contain '=' before building mapping
    for arg in sys.argv[2:]:
        if "=" not in arg:
            print("Usage: render_template.py <template-file> [KEY=VALUE ...]", file=sys.stderr)
            return 1
    mapping = dict(arg.split("=", 1) for arg in sys.argv[2:])
    print(render(template_path.read_text(encoding="utf-8"), mapping), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
