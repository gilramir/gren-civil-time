#!/usr/bin/env python3
"""Regenerate tests/src/Examples/*.geng from the doc comments in src/Civil.

Every indented block in a doc comment that has a `-->` in it is an example:
the expression before the arrow is expected to equal the value after it. One
block can hold several, one per arrow, and an expression can run over several
lines. Each source module gets its own test module, because the examples in
`Civil.Date` need core's `Time` under that name and the examples in
`Civil.Time` need `Civil.Time` under it.

The Gren itself lives in tools/templates/Examples.geng. The output is not
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
        "source": "src/Civil/Date.geng",
        "module": "Examples.Date",
        "imports": ["import Civil.Date as Date", "import Time"],
    },
    {
        "source": "src/Civil/Time.geng",
        "module": "Examples.Time",
        "imports": ["import Civil.Time as Time"],
    },
    {
        "source": "src/Civil/Offset.geng",
        "module": "Examples.Offset",
        "imports": ["import Civil.Offset as Offset"],
    },
    {
        "source": "src/Civil/DateTime.geng",
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


def declares(lines, after):
    """The name of the thing a doc comment is the documentation for: the
    identifier the first line after it starts with. The comment at the top of
    the file documents the module, and is followed by the imports."""
    for line in lines[after:]:
        words = line.replace("(", " ").split()
        if not words or words[0] == "--":
            continue
        if words[0] == "import":
            return "the module"
        if words[0] == "type":
            return words[2] if words[1] == "alias" else words[1]
        return words[0]
    return "the module"


def code_blocks(path):
    """The indented blocks inside doc comments, as (first line number, lines,
    what the comment documents) with the indent removed. A block has to follow
    a blank line, which is what keeps the continuation line of a bullet point
    from looking like code."""
    lines = open(path).read().split("\n")
    blocks = []
    pending = []
    block = None
    in_doc = False
    after_blank = False

    def close():
        nonlocal block
        if block:
            pending.append(block)
        block = None

    for number, line in enumerate(lines, 1):
        if not in_doc:
            if line.startswith("{-|") and "-}" not in line:
                in_doc = True
                after_blank = True
            continue
        if line.rstrip().endswith("-}"):
            in_doc = False
            close()
            name = declares(lines, number)
            blocks.extend((first, block_lines, name) for first, block_lines in pending)
            pending = []
            continue
        if line.startswith(INDENT) and (block or after_blank):
            if block is None:
                block = (number, [])
            block[1].append(line[len(INDENT):])
        else:
            close()
        after_blank = line.strip() == ""
    return blocks


def name_of(declared, expression):
    """What to call the test for one example. The line it came from would move
    whenever anything above it changed, and a name that moves cannot be
    followed from one run to the next, so the name is what the example says
    instead: the thing being documented, and the expression itself on one
    line."""
    one_line = " ".join(line.strip() for line in expression if line.strip())
    return "%s: %s" % (declared, one_line)


def examples(path):
    found = []
    for first, lines, declared in code_blocks(path):
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
                "name": name_of(declared, expression),
                "expression": expression,
                "expected": after.strip(),
            })
            expression = []
        if expression:
            sys.exit("%s:%d: code after the last arrow" % (path, first))
    seen = {}
    for example in found:
        seen[example["name"]] = seen.get(example["name"], 0) + 1
    for name, count in seen.items():
        if count > 1:
            # Two tests under one name are one test as far as any history of
            # the runs is concerned. Say so rather than generate them.
            sys.exit("%s: %d examples would be named %s" % (path, count, name))
    return found


def quoted(text):
    """Text as it has to be written between the quotes of a Gren string."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def main():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["quoted"] = quoted
    template = env.get_template("Examples.geng")
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
        out_path = "tests/src/%s.geng" % spec["module"].replace(".", "/")
        with open(out_path, "w") as out:
            out.write(rendered)
        print("%s: %d examples" % (out_path, len(found)))


if __name__ == "__main__":
    main()
