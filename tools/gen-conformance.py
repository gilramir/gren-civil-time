#!/usr/bin/env python3
"""Regenerate tests/src/Conformance.geng from the official TOML test suite.

Walks the date and time directories of vendor/toml-test, keeps only the
files listed in the 1.1.0 manifest, and pairs each valid .toml value with the
expected value from its .json sibling. The Gren itself lives in
tools/templates/Conformance.geng.

One normalisation is applied to the expected strings, so that the Gren suite
can compare text and say something useful when it differs: toml-test writes a
fraction to three places (.600) and this package strips trailing zeroes (.6).
toml-test itself compares datetimes by parsing them, so the two agree where it
counts.

An invalid file contributes its first assignment only; every file in these
directories has exactly one.

The counts in the guard test are written from the tables, so an extractor that
silently stopped finding cases cannot produce a file that passes.

Run from the package root:  python3 tools/gen-conformance.py
"""

import json
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader

TESTS = "vendor/toml-test/tests"
DIRS = ["datetime", "local-date", "local-time", "local-datetime"]
KINDS = ("datetime", "datetime-local", "date-local", "time-local")

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def normalise(value):
    """This package's normal form: trailing zeroes off the fraction, and an
    all-zero fraction gone entirely."""
    match = re.search(r"\.(\d+)", value)
    if not match:
        return value
    digits = match.group(1).rstrip("0")
    return value[:match.start()] + ("." + digits if digits else "") + value[match.end():]


def right_hand_side(line):
    value = line[line.index("=") + 1:].strip()
    if "#" in value:
        value = value[:value.index("#")].strip()
    return value


def assignments(path):
    """key -> the text on the right of the =, for the simple one-per-line
    files these directories contain."""
    found = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        found[line[:line.index("=")].strip().strip('"')] = right_hand_side(line)
    return found


def collect(manifest):
    good, bad = [], []
    for directory in DIRS:
        valid = os.path.join(TESTS, "valid", directory)
        if os.path.isdir(valid):
            for name in sorted(os.listdir(valid)):
                if not name.endswith(".json"):
                    continue
                rel = "valid/%s/%s.toml" % (directory, name[:-5])
                if rel not in manifest:
                    continue
                expected = json.load(open(os.path.join(valid, name)))
                source = assignments(os.path.join(valid, name[:-5] + ".toml"))
                for key, value in expected.items():
                    if not isinstance(value, dict) or value.get("type") not in KINDS:
                        continue
                    if key not in source:
                        sys.exit("%s: no assignment for key %r" % (rel, key))
                    good.append({
                        "kind": value["type"],
                        "text": source[key],
                        "want": normalise(value["value"]),
                        "file": rel,
                    })

        invalid = os.path.join(TESTS, "invalid", directory)
        if os.path.isdir(invalid):
            for name in sorted(os.listdir(invalid)):
                if not name.endswith(".toml"):
                    continue
                rel = "invalid/%s/%s" % (directory, name)
                if rel not in manifest:
                    continue
                for line in open(os.path.join(invalid, name)):
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    bad.append({"text": right_hand_side(line), "file": rel})
                    break
    return good, bad


def gren_string(text):
    """The contents of a Gren string literal, quoted as one."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def main():
    manifest = set(open(os.path.join(TESTS, "files-toml-1.1.0")).read().split())
    good, bad = collect(manifest)
    if not good or not bad:
        sys.exit("found no cases; is vendor/toml-test checked out?")

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["gren_string"] = gren_string
    rendered = env.get_template("Conformance.geng").render(good=good, bad=bad)
    with open("tests/src/Conformance.geng", "w") as out:
        out.write(rendered)
    print("%d valid, %d invalid" % (len(good), len(bad)))


if __name__ == "__main__":
    main()
