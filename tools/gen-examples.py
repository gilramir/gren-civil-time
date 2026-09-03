#!/usr/bin/env python3
"""Regenerate tests/src/Examples/*.gren from the doc comments in src/Civil.

Every indented block in a doc comment that has a `-->` in it is an example:
the expression before the arrow is expected to equal the value after it. One
block can hold several, one per arrow, and an expression can run over several
lines. Each source module gets its own test module, because the examples in
`Civil.Date` need core's `Time` under that name and the examples in
`Civil.Time` need `Civil.Time` under it.

The Gren itself lives in tools/templates/Examples.gren. The output is not
formatted here; `devbox run gen` runs gren-format over it afterwards.

Run from the package root:  python3 tools/gen-examples.py
"""

import os
import sys

from jinja2 import Environment, FileSystemLoader

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# What each test module imports: the module under test under the name its
# examples use, and whatever else those examples mention.
MODULES = [
    {
        "source": "src/Civil/Date.gren",
        "module": "Examples.Date",
        "imports": ["import Civil.Date as Date", "import Time"],
    },
    {
        "source": "src/Civil/Time.gren",
        "module": "Examples.Time",
        "imports": ["import Civil.Time as Time"],
    },
    {
        "source": "src/Civil/Offset.gren",
        "module": "Examples.Offset",
        "imports": ["import Civil.Offset as Offset"],
    },
    {
        "source": "src/Civil/DateTime.gren",
        "module": "Examples.DateTime",
        "imports": [
            "import Civil.Date as Date",
            "import Civil.DateTime as DateTime",
            "import Civil.Offset as Offset",
            "import Civil.Time as Time",
            "import Time as CoreTime",
        ],
    },
]

INDENT = "    "


def code_blocks(path):
    """The indented blocks inside doc comments, as (first line number, lines)
    with the indent removed. A block has to follow a blank line, which is what
    keeps the continuation line of a bullet point from looking like code."""
    blocks = []
    block = None
    in_doc = False
    after_blank = False
    for number, line in enumerate(open(path).read().split("\n"), 1):
        if not in_doc:
            if line.startswith("{-|") and "-}" not in line:
                in_doc = True
                after_blank = True
            continue
        if line.rstrip().endswith("-}"):
            in_doc = False
            if block:
                blocks.append(block)
            block = None
            continue
        if line.startswith(INDENT) and (block or after_blank):
            if block is None:
                block = (number, [])
            block[1].append(line[len(INDENT):])
        else:
            if block:
                blocks.append(block)
            block = None
        after_blank = line.strip() == ""
    return blocks


def examples(path):
    found = []
    for first, lines in code_blocks(path):
        if not any("-->" in line for line in lines):
            continue
        expression = []
        start = first
        for offset, line in enumerate(lines):
            if "-->" not in line:
                if not expression:
                    start = first + offset
                expression.append(line.rstrip())
                continue
            before, after = line.split("-->", 1)
            if before.strip():
                if not expression:
                    start = first + offset
                expression.append(before.rstrip())
            if not expression:
                sys.exit("%s:%d: an arrow with nothing before it" % (path, first + offset))
            found.append({
                "where": "%s:%d" % (path, start),
                "expression": expression,
                "expected": after.strip(),
            })
            expression = []
        if expression:
            sys.exit("%s:%d: code after the last arrow" % (path, first))
    return found


def main():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("Examples.gren")
    os.makedirs("tests/src/Examples", exist_ok=True)
    for spec in MODULES:
        found = examples(spec["source"])
        if not found:
            sys.exit("%s: found no examples" % spec["source"])
        rendered = template.render(
            module=spec["module"],
            source=spec["source"],
            imports=spec["imports"],
            examples=found,
        )
        out_path = "tests/src/%s.gren" % spec["module"].replace(".", "/")
        with open(out_path, "w") as out:
            out.write(rendered)
        print("%s: %d examples" % (out_path, len(found)))


if __name__ == "__main__":
    main()
