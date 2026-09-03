#!/usr/bin/env python3
"""Regenerate tests/src/Conformance.gren from the official TOML test suite.

Walks the date and time directories of vendor/toml-test, keeps only the
files listed in the 1.1.0 manifest, and pairs each valid .toml value with the
expected value from its .json sibling.

Two normalisations are applied to the expected strings, both so that the Gren
suite can compare text and say something useful when it differs:

  * toml-test writes a fraction to three places (.600); this package strips
    trailing zeroes (.6). toml-test itself compares datetimes by parsing them,
    so the two agree where it counts.

The counts in the guard test are written from the tables, so an extractor that
silently stopped finding cases cannot produce a file that passes.

Run from the package root:  python3 tools/gen-conformance.py
"""

import json
import os
import re
import sys

TESTS = "vendor/toml-test/tests"
DIRS = ["datetime", "local-date", "local-time", "local-datetime"]
KINDS = ("datetime", "datetime-local", "date-local", "time-local")

HEAD = """module Conformance exposing (conformanceSuite)

{-| Every date and time in the official TOML test suite.

The cases are lifted straight out of `toml-test`, filtered to the
`files-toml-1.1.0` manifest: 32 values that must parse, and 70 that must not.
This is the suite the TOML parser will eventually be scored against, and these
are the parts of it this package is responsible for -- so it is worth failing
here, where the message says which spelling broke, rather than three packages
later where it says a key had the wrong value.

The expected strings are `toml-test`'s own, with one change: it writes a
fraction to three places (`.600`) and this module strips trailing zeroes
(`.6`). `toml-test` compares datetimes by parsing them rather than as text, so
the two agree where it counts; the normalisation here is only so that this
suite can compare strings and say something useful when they differ.

The invalid cases are checked against all three of [`Civil.Date`](Civil-Date),
[`Civil.Time`](Civil-Time) and [`Civil.DateTime`](Civil-DateTime), because a
string that is not a date-time must not turn out to be a date either.

@docs conformanceSuite

-}

import Array exposing (Array)
import Civil.Date as Date
import Civil.DateTime as DateTime
import Civil.Time as Time
import Expect
import Maybe exposing (Maybe(..))
import String
import Task
import Test.Runner.UnitNode as U


type alias Good =
    { kind : String, text : String, want : String, file : String }


type alias Bad =
    { text : String, file : String }


good : Array Good
good =
"""

MID = """    ]


bad : Array Bad
bad =
"""

TAIL = """    ]


{-| Parse a value the way its type says to, and refuse it if the offset came
out on the wrong side of the local/absolute line. A `datetime-local` that
parsed with an offset is not the value the suite asked for.
-}
render : String -> String -> Maybe String
render kind text =
    when kind is
        "date-local" ->
            Date.fromString text
                |> Maybe.map Date.toString

        "time-local" ->
            Time.fromString text
                |> Maybe.map Time.toString

        "datetime-local" ->
            DateTime.fromString text
                |> Maybe.andThen
                    (\\dt ->
                        if DateTime.isLocal dt then
                            Just (DateTime.toString dt)

                        else
                            Nothing
                    )

        _ ->
            DateTime.fromString text
                |> Maybe.andThen
                    (\\dt ->
                        if DateTime.isLocal dt then
                            Nothing

                        else
                            Just (DateTime.toString dt)
                    )


{-| Nothing in this package should read this string as anything.
-}
readsAsSomething : String -> Bool
readsAsSomething text =
    (Date.fromString text /= Nothing)
        || (Time.fromString text /= Nothing)
        || (DateTime.fromString text /= Nothing)


{-| -}
conformanceSuite : U.Suite
conformanceSuite =
    U.suite
        { name = "Conformance"
        , setUpSuite = U.noSuiteFixture
        , tearDownSuite = U.noTearDown
        , setUp = \\_ -> Task.succeed {}
        , tearDown = U.noTearDown
        , tests =
            -- A generated table that came out empty would pass every test
            -- below it without running anything. These are the counts the
            -- extractor reported; if they drift, the extractor changed.
            [ U.test "the tables are the size toml-test says they are" <| \\_ ->
                Task.succeed
                    (Expect.equal { good = %d, bad = %d }
                        { good = Array.length good, bad = Array.length bad }
                    )
            , U.test "every date-time toml-test accepts parses to the expected value" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (good
                            |> Array.keepIf (\\g -> render g.kind g.text /= Just g.want)
                            |> Array.map
                                (\\g ->
                                    g.file
                                        ++ ": "
                                        ++ g.text
                                        ++ " -> "
                                        ++ describe (render g.kind g.text)
                                        ++ ", wanted "
                                        ++ g.want
                                )
                        )
                    )
            , U.test "and every one it rejects is rejected by all three modules" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (bad
                            |> Array.keepIf (\\b -> readsAsSomething b.text)
                            |> Array.map (\\b -> b.file ++ ": " ++ b.text)
                        )
                    )
            ]
        }


describe : Maybe String -> String
describe result =
    when result is
        Just text ->
            text

        Nothing ->
            "nothing"
"""


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
                    good.append((rel, source[key], value["type"], value["value"]))

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
                    bad.append((rel, right_hand_side(line)))
                    break
    return good, bad


def escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def table(rows):
    lines = ["    [ " + rows[0]]
    lines += ["    , " + row for row in rows[1:]]
    return "\n".join(lines) + "\n"


def main():
    manifest = set(open(os.path.join(TESTS, "files-toml-1.1.0")).read().split())
    good, bad = collect(manifest)
    if not good or not bad:
        sys.exit("found no cases; is vendor/toml-test checked out?")

    good_rows = [
        '{ kind = "%s", text = "%s", want = "%s", file = "%s" }'
        % (kind, escape(text), escape(normalise(want)), path)
        for path, text, kind, want in good
    ]
    bad_rows = [
        '{ text = "%s", file = "%s" }' % (escape(text), path)
        for path, text in bad
    ]

    with open("tests/src/Conformance.gren", "w") as out:
        out.write(HEAD + table(good_rows)
                  + MID + table(bad_rows)
                  + (TAIL % (len(good), len(bad))))
    print("%d valid, %d invalid" % (len(good), len(bad)))


if __name__ == "__main__":
    main()
