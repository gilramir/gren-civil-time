# gren-civil-time

Calendar dates and clock times, with or without an offset from UTC.

Gren's core `Time` module deals in *moments*. A `Posix` is one exact point in
time, the same everywhere in the world, and that is the right type for
recording when something happened. It is the wrong type for a birthday, a
shop's opening hour, the date on an invoice, or the `1979-05-27T07:32:00` in a
config file. Those are readings from a calendar and a clock. They only become
moments once you know where they were read.

This package provides the types for those readings. This package was originally
written to support reading TOML files, so that's why there are many references
to TOML in the docs and in the tests.

```gren
import Civil.DateTime as DateTime

DateTime.fromString "1979-05-27 07:32:00-07:00"
    |> Maybe.map DateTime.toString
--> Just "1979-05-27T07:32:00-07:00"
```

## The four shapes

[RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) is the standard for writing
dates and times as text, and TOML uses it for its date and time values. Both
distinguish four shapes. So does this package:

| example | what it is | module |
|---|---|---|
| `1979-05-27` | a date | `Civil.Date` |
| `07:32:00` | a time of day | `Civil.Time` |
| `1979-05-27T07:32:00` | a date and a time, but still not a moment | `Civil.DateTime` |
| `1979-05-27T07:32:00-07:00` | a moment | `Civil.DateTime` |

The last shape carries an *offset*: how far the clock was ahead of or behind
UTC when the reading was taken. That is enough to pin down a moment, so
`DateTime.toPosix` works on it. The third shape has no offset, so `toPosix`
returns `Nothing` for it.

Turning the third shape into a moment needs a time zone, such as
`America/Denver`. A time zone is a set of rules for which offset applies when,
and those rules change over the years. They live in the IANA time zone
database, which is far larger than this package and is deliberately left out
of it.

## Every value is valid

The only way to build a value is through a constructor, and every constructor
checks its input. `2023-02-29`, `24:00:00`, `+25:00` and `1979-5-27` all give
`Nothing`, so code that receives a value never has to check it again.

```gren
Civil.Date.fromString "2100-02-29"   --> Nothing   -- 2100 is not a leap year
Civil.Date.fromString "2024-02-29"   --> a date
```

Years run from 1 to 9999, the range RFC 3339 allows.

## Three ways to write a zero offset

`Z`, `+00:00` and `-00:00` all mean zero minutes from UTC, but RFC 3339 gives
them three different meanings. `Z` says the time is in UTC. `+00:00` is an
ordinary offset that happens to be zero. `-00:00` means the offset is unknown.
`Civil.Offset` keeps the three apart: they are different values under `==`,
but `toMinutes` returns `0` for all of them. Use whichever comparison you need.

## Fractions of a second are kept in full

There is no millisecond or nanosecond limit. The digits after the decimal
point are stored as text, however many there are, so nothing is rounded away.
Trailing zeroes are dropped, so `10:32:00.5` and `10:32:00.50` are the same
value.

## Leap seconds

`23:59:60` parses, because RFC 3339 allows a leap second and a timestamp that
records one is valid. The package does no arithmetic that would need to decide
what a leap second means. `secondOfDay` simply returns `86400` for it, one past
the last ordinary second of the day.

The `60` is checked as a seconds field on its own, not as part of an
`HH:MM:SS` that has to read `23:59:60`. `12:30:60` parses too, and
`secondOfDay` gives it `45060`. That is RFC 3339's grammar, which allows `60`
in the seconds field and leaves the question of whether a leap second was
really inserted at that instant to whoever knows. It has to: a leap second
falls at `23:59:60` UTC, which is some other wall clock at every other offset,
so the same second is `1990-12-31T15:59:60-08:00` in California.

## Tests

```sh
git clone <this repo>     # --recurse-submodules is optional; see below
devbox run test
```

The suite is 101 checks and runs in a few milliseconds.

```
Dates              ok    17/17  (3 ms)
Clocks             ok    33/33  (3 ms)
Conformance        ok     3/3   (1 ms)
Examples.Date      ok    18/18  (0 ms)
Examples.Time      ok    14/14  (0 ms)
Examples.Offset    ok     9/9   (0 ms)
Examples.DateTime  ok     7/7   (1 ms)

Ran 101 tests in 8 ms

OK — 101 passed
```

What each suite checks:

| suite | what it checks |
|---|---|
| `Dates` | Forty dates against Python's `datetime.date`, whose `toordinal` uses the same day numbering as `toRataDie`. Ten are dates where calendar code tends to break and thirty are random across the whole range. Also the constructor and the accessors called directly. |
| `Clocks` | What the TOML suite does not reach: the three zero offsets, the fraction, leap seconds, the `Posix` round trip on both sides of 1970, `toPosix` against Python-computed values for real offsets, and which characters count as digits. |
| `Conformance` | Every date and time in the official [toml-test](https://github.com/toml-lang/toml-test) suite: 32 that must parse and 70 that must not. |
| `Examples.*` | Every `-->` example in the doc comments, 48 of them, checked against the value it claims. |

### The slow checks

```sh
devbox run probe
```

`tests/src/Probe.gren` walks every one of the 3,652,059 days from year 1 to
year 9999, using only the length of each month, and checks at each day that
the day number, the day of the year, the weekday, the text form and the
`Posix` all agree with the walk. It then sends every second of a day through
`Posix` and back, and every offset through text and back. It takes about ten
seconds, so it has its own runner and is not part of `devbox run test`.

### The submodule is only for regenerating tests

`tests/src/Dates.gren`, `tests/src/Conformance.gren` and the four modules
under `tests/src/Examples/` are **generated**, and the generated files are
committed.

The conformance generator reads the TOML test corpus from `vendor/toml-test`,
a git submodule pinned to one commit. It is pinned because the generator
writes the number of cases it found into a guard test. Regenerating against a
newer corpus would change that number and fail the guard. The examples
generator reads the doc comments in `src/`.

The generators do not contain any Gren. The Gren lives in `tools/templates/`,
one Jinja2 template per generated module. Each script gathers its data and
renders its template.

```sh
devbox run gen                       # all three, then gren-format on the examples

python3 tools/gen-dates.py           # needs Python and Jinja2
python3 tools/gen-conformance.py     # also needs the submodule
python3 tools/gen-examples.py        # then gren-format tests/src/Examples/
```

**If you cloned without `--recurse-submodules`**, the tests still pass. Only
the conformance generator fails:

```
FileNotFoundError: [Errno 2] No such file or directory:
    'vendor/toml-test/tests/files-toml-1.1.0'
```

Fetch the submodule in place. No re-clone is needed:

```sh
git submodule update --init
```

`devbox run gen` reproduces every generated file byte for byte, so a diff
after regenerating means a script and its output have drifted apart. Two
safeguards keep a broken generator from producing an empty suite that passes:
`gen-conformance.py` writes the number of cases it found into a guard test,
and `gen-examples.py` refuses to write a module in which it found no examples.
