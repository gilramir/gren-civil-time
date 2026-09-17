#!/usr/bin/env python3
"""Regenerate tests/src/Dates.geng from tools/templates/Dates.geng.

The forty dates it checks come from Python's datetime, whose toordinal is Rata
Die on the same epoch. Ten are chosen (the ends of the range, the century rule,
the exception to it, the Unix epoch) and thirty are drawn at random from a
fixed seed, so the file only changes when this script or the template does.

Run from the package root:  python3 tools/gen-dates.py
"""

import datetime
import os
import random

from jinja2 import Environment, FileSystemLoader

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The ends, the Gregorian changeover, the century rule and its exception, and
# the Unix epoch in case anything has quietly picked one up.
CHOSEN = [
    (1, 1, 1), (1, 12, 31), (1582, 10, 15), (1900, 2, 28), (1900, 3, 1),
    (1970, 1, 1), (2000, 2, 29), (2024, 2, 29), (2100, 2, 28), (9999, 12, 31),
]

MIN_RD, MAX_RD = 1, 3652059


def rows():
    random.seed(20260902)
    picks = list(CHOSEN)
    for _ in range(30):
        rd = random.randint(MIN_RD, MAX_RD)
        picks.append(datetime.date.fromordinal(rd).timetuple()[:3])
    out = []
    for y, m, d in picks:
        date = datetime.date(y, m, d)
        out.append({
            "iso": date.isoformat(),
            "rd": date.toordinal(),
            "wd": WEEKDAYS[date.weekday()],
            "yd": date.timetuple().tm_yday,
        })
    return out


def main():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    rendered = env.get_template("Dates.geng").render(rows=rows())
    with open("tests/src/Dates.geng", "w") as out:
        out.write(rendered)


if __name__ == "__main__":
    main()
