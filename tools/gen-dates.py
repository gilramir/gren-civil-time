#!/usr/bin/env python3
"""Regenerate tests/src/Dates.gren.

The forty dates it checks come from Python's datetime, whose toordinal is Rata
Die on the same epoch. Ten are chosen (the ends of the range, the century rule,
the exception to it, the Unix epoch) and thirty are drawn at random from a
fixed seed, so the file only changes when this script does.

Run from the package root:  python3 tools/gen-dates.py
"""

import datetime
import random

HEAD = """module Dates exposing (datesSuite)

{-| The calendar: Rata Die, weekdays, day of year, and what is not a date.

The expected values come from Python's `datetime.date`, whose `toordinal` is
Rata Die under another name -- `date(1, 1, 1).toordinal()` is `1`, the same
epoch this module uses. Forty dates, ten of them chosen because something
usually breaks there and thirty drawn at random across the whole range, are
checked in both directions.

The dates that break things: the first and last representable days; 1582-10-15,
the first day of the Gregorian calendar, which this module treats as an
ordinary day because a proleptic calendar has to; 1900 and 2100 around the end
of February, where the century rule bites; 2000-02-29, where the exception to
the century rule bites; and 1970-01-01, in case anything has quietly picked up
a Unix epoch.

@docs datesSuite

-}

import Array exposing (Array)
import Civil.Date as Date exposing (Date)
import Expect
import Maybe exposing (Maybe(..))
import Task
import Test.Runner.UnitNode as U
import Time


type alias Row =
    { iso : String, rd : Int, wd : Time.Weekday, yd : Int }


rows : Array Row
rows =
"""

TAIL = """    ]


{-| -}
datesSuite : U.Suite
datesSuite =
    U.suite
        { name = "Dates"
        , setUpSuite = U.noSuiteFixture
        , tearDownSuite = U.noTearDown
        , setUp = \\_ -> Task.succeed {}
        , tearDown = U.noTearDown
        , tests =
            -- READING A DATE AND WRITING IT BACK
            [ U.test "fromString and toString are inverses on every row" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (rows
                            |> Array.keepIf
                                (\\row ->
                                    (Date.fromString row.iso |> Maybe.map Date.toString)
                                        /= Just row.iso
                                )
                            |> Array.map .iso
                        )
                    )
            -- RATA DIE, AGAINST PYTHON
            , U.test "toRataDie agrees with Python's toordinal" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (rows
                            |> Array.keepIf
                                (\\row ->
                                    (Date.fromString row.iso |> Maybe.map Date.toRataDie)
                                        /= Just row.rd
                                )
                            |> Array.map .iso
                        )
                    )
            , U.test "fromRataDie undoes it" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (rows
                            |> Array.keepIf
                                (\\row ->
                                    (Date.fromRataDie row.rd |> Maybe.map Date.toString)
                                        /= Just row.iso
                                )
                            |> Array.map .iso
                        )
                    )
            -- WHAT THE DAY NUMBER IS GOOD FOR
            , U.test "weekday agrees with Python" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (rows
                            |> Array.keepIf
                                (\\row ->
                                    (Date.fromString row.iso |> Maybe.map Date.weekday)
                                        /= Just row.wd
                                )
                            |> Array.map .iso
                        )
                    )
            , U.test "ordinalDay agrees with Python's tm_yday" <| \\_ ->
                Task.succeed
                    (Expect.equal []
                        (rows
                            |> Array.keepIf
                                (\\row ->
                                    (Date.fromString row.iso |> Maybe.map Date.ordinalDay)
                                        /= Just row.yd
                                )
                            |> Array.map .iso
                        )
                    )
            -- THE ENDS OF THE RANGE
            , U.test "the range stops at year 1 and year 9999" <| \\_ ->
                Task.succeed
                    (Expect.equal [ Nothing, Nothing, Just 1, Just 3652059 ]
                        [ Date.fromRataDie 0 |> Maybe.map Date.toRataDie
                        , Date.fromRataDie 3652060 |> Maybe.map Date.toRataDie
                        , Date.fromString "0001-01-01" |> Maybe.map Date.toRataDie
                        , Date.fromString "9999-12-31" |> Maybe.map Date.toRataDie
                        ]
                    )
            , U.test "and addDays refuses to leave it" <| \\_ ->
                Task.succeed
                    (Expect.equal [ Nothing, Nothing, Just "9999-12-31" ]
                        [ Date.fromString "0001-01-01"
                            |> Maybe.andThen (Date.addDays -1)
                            |> Maybe.map Date.toString
                        , Date.fromString "9999-12-31"
                            |> Maybe.andThen (Date.addDays 1)
                            |> Maybe.map Date.toString
                        , Date.fromString "9999-12-30"
                            |> Maybe.andThen (Date.addDays 1)
                            |> Maybe.map Date.toString
                        ]
                    )
            -- THE LEAP YEAR RULE, WHICH IS THE POINT OF VALIDATING AT ALL
            , U.test "February gets its 29th only in a leap year" <| \\_ ->
                Task.succeed
                    (Expect.equal [ True, False, True, False, True ]
                        [ Date.isLeapYear 2000
                        , Date.isLeapYear 2100
                        , Date.isLeapYear 2024
                        , Date.isLeapYear 2023
                        , Date.isLeapYear 1600
                        ]
                    )
            , U.test "so 2024-02-29 is a date and 2100-02-29 is not" <| \\_ ->
                Task.succeed
                    (Expect.equal [ True, False, True, False ]
                        [ Date.fromString "2024-02-29" /= Nothing
                        , Date.fromString "2100-02-29" /= Nothing
                        , Date.fromString "2000-02-29" /= Nothing
                        , Date.fromString "2023-02-29" /= Nothing
                        ]
                    )
            , U.test "daysInMonth covers every month and refuses the rest" <| \\_ ->
                Task.succeed
                    (Expect.equal
                        [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 0, 0 ]
                        (Array.map
                            (\\m -> Date.daysInMonth { year = 2023, month = m })
                            [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0, 13 ]
                        )
                    )
            -- THE SPELLINGS TOML REJECTS, WHICH ARE THE SAME ONES RFC 3339 DOES
            , U.test "fromString wants exactly 4-2-2 digits and nothing else" <| \\_ ->
                Task.succeed
                    (Expect.equal (Array.repeat 8 Nothing)
                        [ Date.fromString "1979-5-05"
                        , Date.fromString "1979-05-5"
                        , Date.fromString "979-05-05"
                        , Date.fromString "01979-05-05"
                        , Date.fromString "1979-05-05T00:00:00"
                        , Date.fromString "1979-05-05 "
                        , Date.fromString "+979-05-05"
                        , Date.fromString ""
                        ]
                    )
            , U.test "and a month or day outside the calendar" <| \\_ ->
                Task.succeed
                    (Expect.equal (Array.repeat 6 Nothing)
                        [ Date.fromString "2006-13-01"
                        , Date.fromString "2007-00-01"
                        , Date.fromString "2006-01-32"
                        , Date.fromString "2006-01-00"
                        , Date.fromString "1988-02-30"
                        , Date.fromString "2006-04-31"
                        ]
                    )
            -- ARITHMETIC
            , U.test "addDays and difference undo each other" <| \\_ ->
                Task.succeed
                    (Expect.equal (Just 738945)
                        (Date.fromString "2024-02-29"
                            |> Maybe.andThen (Date.addDays 10000)
                            |> Maybe.andThen (Date.addDays -10000)
                            |> Maybe.map Date.toRataDie
                        )
                    )
            , U.test "difference counts the days between, signed" <| \\_ ->
                Task.succeed
                    (Expect.equal [ Just 2, Just -2, Just 0 ]
                        [ Maybe.map2 Date.difference (date "2024-02-28") (date "2024-03-01")
                        , Maybe.map2 Date.difference (date "2024-03-01") (date "2024-02-28")
                        , Maybe.map2 Date.difference (date "2024-03-01") (date "2024-03-01")
                        ]
                    )
            ]
        }


date : String -> Maybe Date
date =
    Date.fromString
"""

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
        out.append(
            '{ iso = "%s", rd = %d, wd = Time.%s, yd = %d }'
            % (date.isoformat(), date.toordinal(),
               WEEKDAYS[date.weekday()], date.timetuple().tm_yday)
        )
    return out


def main():
    body = rows()
    lines = ["    [ " + body[0]]
    lines += ["    , " + row for row in body[1:]]
    with open("tests/src/Dates.gren", "w") as out:
        out.write(HEAD + "\n".join(lines) + "\n" + TAIL)


if __name__ == "__main__":
    main()
