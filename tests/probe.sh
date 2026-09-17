#!/bin/bash
# The slow checks: every day of the calendar, every second of a day, every
# offset. A few seconds rather than a few milliseconds, which is why they are
# not in run.sh. See Probe.gren.
set -e
cd "$(dirname "$0")"
geng make Probe --output=probe >/dev/null
exec node probe "$@"
