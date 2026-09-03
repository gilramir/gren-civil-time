# gren-civil-time

Dates and times of day with no instant attached.

Gren's `Time` module is about *absolute* time: a `Posix` is a moment, the same
moment everywhere, and that is the right type for when something happened. It
is the wrong type for a birthday, an opening hour, a date on an invoice, or the
`1979-05-27T07:32:00` in a config file. Those are readings on a calendar and a
clock. They become moments only when someone supplies a place, and often nobody
ever does.

This package is the other type.

```gren
import Civil.DateTime as DateTime

DateTime.fromString "1979-05-27 07:32:00-07:00"
    |> Maybe.map DateTime.toString
--> Just "1979-05-27T07:32:00-07:00"
```

## The four shapes

RFC 3339 and TOML both distinguish four, and so does this package:

| example | what it is | module |
|---|---|---|
| `1979-05-27` | a date | `Civil.Date` |
| `07:32:00` | a time of day | `Civil.Time` |
| `1979-05-27T07:32:00` | both, still not a moment | `Civil.DateTime` |
| `1979-05-27T07:32:00-07:00` | a moment | `Civil.DateTime` |

The fourth is the only one with a `Posix`, and `toPosix` returns `Nothing` for
the third. Turning a local date-time into a moment needs a time zone rather than
an offset, and a time zone needs the IANA database — which is a much larger
thing than this package and is deliberately not in it.

## What it will not let you build

Every value that exists is a real one. `2023-02-29`, `24:00:00`, `+25:00` and
`1979-5-27` are all `Nothing`, so nothing downstream has to wonder.

```gren
Civil.Date.fromString "2100-02-29"   --> Nothing   -- not a leap year
Civil.Date.fromString "2024-02-29"   --> a date
```

The range is year 1 through year 9999, which is RFC 3339's.

## Three ways to write zero

`Z`, `+00:00` and `-00:00` are all zero minutes from UTC, and RFC 3339 gives
them three different meanings — the last is its "offset unknown". `Civil.Offset`
keeps them apart under `==` and collapses them under `toMinutes`, so you can ask
either question.

## Fractions are kept

There is no millisecond limit and no nanosecond limit. The digits after the
decimal point are stored as they were given, however many, because deciding
that the twelfth one does not matter is not this package's decision. Trailing
zeroes do come off, so that `10:32:00.5` and `10:32:00.50` are one value.

## Leap seconds

`23:59:60` parses, because RFC 3339 allows it and a timestamp that records one
is not malformed. No arithmetic here pretends to know what it means:
`secondOfDay` returns `86400`, which is honest rather than useful.

## Tests

```sh
git clone --recurse-submodules <this repo>
devbox run test
```

36 checks. The calendar is checked against Python's `datetime.date` in both
directions — its `toordinal` is Rata Die on the same epoch — over forty dates,
ten chosen where things break and thirty drawn at random across the whole
range. The parsing is checked against every date and time in the official
[toml-test](https://github.com/toml-lang/toml-test) suite: 32 that must parse
and 70 that must not.

Both tables are generated. `tools/gen-dates.py` needs nothing;
`tools/gen-conformance.py` reads `vendor/toml-test`, a submodule pinned to a
particular commit so that regenerating twice gives the same file. They
rewrite their files, and the second one writes the row counts into a guard test
so that an extractor which quietly stopped finding cases cannot produce a suite
that passes.

## License

ISC.
