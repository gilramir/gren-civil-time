# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## About this project

`gren-civil-time` is calendar time, as opposed to core's `Time`, which is
absolute time. A `Posix` is a moment; a `Civil.DateTime` usually is not. See
[README.md](README.md) for the four shapes and why the distinction is the whole
point of the package.

Four modules, each depending only on the ones above it:

- `Civil.Offset` — a fixed offset from UTC. Not a time zone.
- `Civil.Date` — a Gregorian date, years 1 to 9999.
- `Civil.Time` — a time of day, with an exact fraction.
- `Civil.DateTime` — the two together, with or without an offset.

## Commands

Everything runs inside devbox; `gren` and node 22 are not on `PATH` otherwise.

```sh
devbox run build    # compile the package
devbox run docs     # check the doc comments parse
devbox run test     # tests/run.sh: 99 checks, milliseconds
devbox run probe    # tests/probe.sh: the exhaustive checks, about ten seconds
devbox run gen      # regenerate the six generated test modules, and format them
```

Format sources after editing them, especially after scripted edits:

```sh
gren-format             # in place; run in the package root for src/, in tests/ for the tests
gren-format --diff      # what would change
```

`gren-format` takes its files from the `gren.json` of the directory it runs
in, so it has to be run twice: once here and once in `tests/`. Naming a
directory on the command line does not recurse into it.

## The platform facts that govern the implementation

**Gren's `//` truncates its result to 32 bits.** It is `(a / b) | 0`
underneath. Every `//` in `Civil.Date` is on a quotient that stays under 2^24 by
construction — an era, a day of the era, a month index. That is an invariant to
preserve. Where a quotient can be large, as in `DateTime.fromPosix`, the code
goes through `Math.floor` on a `Float` instead; that also gets the sign right
below the epoch, which `//` would not.

**`modBy` is `Math.modBy`, not `Basics.modBy`.**

**A custom type variant takes at most one parameter.** Use a record.

## Invariants

**Every value that exists is valid.** The constructors are the only way in and
all of them check. Nothing downstream re-validates, and nothing should have to.

**`==` is equality of the value, not of the spelling.** `Civil.Time` strips
trailing zeroes from the fraction for exactly this reason. The one deliberate
exception is `Civil.Offset`, where `Z`, `+00:00` and `-00:00` are three values
because RFC 3339 gives them three meanings; `toMinutes` is the numeric view that
collapses them.

**The source spelling is not preserved and is not meant to be.** `1987-07-05
17:45:00z` reads back as `1987-07-05T17:45:00Z`. A caller that needs the
original text has to keep the original text; a value cannot hold both. This is
why `gren-toml` keeps raw literals alongside parsed values rather than asking
this package to remember them.

## Tests

`tests/src/Dates.gren`, `tests/src/Conformance.gren` and the four modules under
`tests/src/Examples/` are **generated**. The Gren lives in `tools/templates/`,
as Jinja2 templates named after the modules they produce; the scripts in
`tools/` supply the data and render them. Edit whichever of the script or the
template the change belongs in, then run `devbox run gen` from the package
root. `gen-conformance.py` reads `vendor/toml-test`, which is a submodule: `git
submodule update --init` if the directory is empty. `gen-examples.py` reads the
`-->` examples out of the doc comments in `src/`, so a doc example is a test:
one that lies fails the build.

`devbox run gen` reproduces every generated file byte for byte, so a diff after
regenerating means the sources and the file have drifted. The Dates and
Conformance templates are written so that `gren-format` is a no-op on their
output; the Examples output is formatted by the `gen` script itself, because the
expressions come from the doc comments and are not under the template's
control. Keep it that way: after changing the Dates template, check that
`gren-format --diff` in `tests/` is still empty.

The templates are not valid Gren on their own -- `gren-format` is for the output
in `tests/src/`, never for `tools/templates/`.

`tests/src/Clocks.gren` is hand written and covers what the TOML suite does not
reach: the three zero offsets, the fraction, leap seconds, the `Posix` round
trip on both sides of the epoch, `toPosix` against Python-computed values, the
constructors and accessors called directly, and non-ASCII digits.

`tests/src/Probe.gren` is the exhaustive walk: every day of the calendar,
every second of a day, every offset. It has its own runner, `tests/probe.sh`,
and is deliberately not in `run.sh`; the fast suite must stay fast.

The conformance table's row counts are written into a guard test by the
generator. Do not hand-edit them — an extractor that silently found nothing
would otherwise produce a suite that passes without checking anything.
