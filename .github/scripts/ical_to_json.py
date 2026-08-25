#!/usr/bin/env python3
"""eviivo iCal -> blocked-dates.json for the Silent Waters estimator.

Reads an iCal file, collects every VEVENT's DTSTART..DTEND as blocked
NIGHTS, and writes JSON of the shape the page expects:

    { "updated": "<ISO timestamp>", "nights": ["YYYY-MM-DD", ...] }

DTEND is exclusive, exactly as RFC 5545 defines it for DATE values: the
end date is the checkout day and is NOT a blocked night, so a new stay
may check in on that day. A DTSTART with no DTEND blocks the single
night of DTSTART.

Usage: ical_to_json.py <ical-file> <output-json>
Exits non-zero on any parse problem so the workflow fails WITHOUT
touching an existing blocked-dates.json — stale data beats no data.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone


def parse_ical_date(value):
    """20261224 or 20261224T140000Z (or with TZID) -> date."""
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", value.strip())
    if not m:
        raise ValueError("unparseable iCal date: %r" % value)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def unfold(text):
    """RFC 5545 line unfolding: a line starting with space/tab continues
    the previous line."""
    return re.sub(r"\r?\n[ \t]", "", text)


def blocked_nights(ical_text):
    nights = set()
    events = re.findall(
        r"BEGIN:VEVENT(.*?)END:VEVENT", unfold(ical_text), re.S)
    if not events and "BEGIN:VCALENDAR" not in ical_text:
        raise ValueError("input does not look like an iCal file")
    for body in events:
        dtstart = re.search(r"^DTSTART[^:]*:(\S+)", body, re.M)
        dtend = re.search(r"^DTEND[^:]*:(\S+)", body, re.M)
        if not dtstart:
            continue
        start = parse_ical_date(dtstart.group(1))
        # DTEND exclusive; a missing DTEND means the single night of DTSTART.
        end = parse_ical_date(dtend.group(1)) if dtend else start + timedelta(days=1)
        d = start
        guard = 0
        while d < end and guard < 3660:  # ~10 years: runaway guard
            nights.add(d.isoformat())
            d += timedelta(days=1)
            guard += 1
    return sorted(nights)


def main():
    if len(sys.argv) != 3:
        print("usage: ical_to_json.py <ical-file> <output-json>", file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        nights = blocked_nights(f.read())
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nights": nights,
    }
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")
    print("wrote %d blocked nights" % len(nights))
    return 0


if __name__ == "__main__":
    sys.exit(main())
