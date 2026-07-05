#!/usr/bin/env python3
"""Escape a label for a shields.io static badge.

shields treats '-', '_' and space specially in the label/message segments:
a literal '-' is written '--', a literal '_' is written '__', and a space
is written '_'. SPDX license ids (e.g. Apache-2.0, BSD-3-Clause) need this
so their hyphens survive into the badge.
"""
import sys


def shields_escape(label):
    return label.replace("_", "__").replace("-", "--").replace(" ", "_")


def main():
    if len(sys.argv) != 2:
        print("Usage: shields_escape.py <label>", file=sys.stderr)
        return 1
    print(shields_escape(sys.argv[1]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
