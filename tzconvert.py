#!/usr/bin/env python3
"""Timezone-conversion CLI: convert one wall time between IANA zones."""

import argparse
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATETIME_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$")
EXPECTED_FORMAT = "YYYY-MM-DD HH:MM"
USAGE = "python3 tzconvert.py DATETIME --from SRC_TZ --to DST_TZ"


def build_parser():
    return argparse.ArgumentParser(
        prog="python3 tzconvert.py",
        usage=USAGE,
        allow_abbrev=False,
        description=(
            "Convert one date-time from one IANA time zone to another.\n"
            "\n"
            "DATETIME is the date-time to convert, in exactly the format "
            "YYYY-MM-DD HH:MM (four-digit year, two-digit month, day, hour "
            "00-23, and minute 00-59, zero-padded, with a single space "
            "separator, e.g. 2024-01-15 12:00). The value must be a real "
            "calendar date-time and carries no seconds, no T separator, "
            "no UTC offset, and no zone suffix.\n"
            "\n"
            "--from SRC_TZ is the source IANA time zone name "
            "(e.g. America/New_York, UTC). Case-sensitive.\n"
            "--to DST_TZ is the destination IANA time zone name "
            "(e.g. America/New_York, UTC). Case-sensitive.\n"
            "\n"
            "Zones must be IANA time zone names loadable via the "
            "standard-library zoneinfo database (for example "
            "America/New_York and UTC). Zone abbreviations such as EST "
            "and fixed offsets such as +05:00 are not accepted."
        ),
        epilog=(
            "examples:\n"
            '  python3 tzconvert.py "2024-01-15 12:00" '
            "--from America/New_York --to UTC\n"
            "  -> 2024-01-15 17:00\n"
            "\n"
            '  python3 tzconvert.py "2024-01-15 12:00" '
            "--from UTC --to Asia/Tokyo\n"
            "  -> 2024-01-15 21:00"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def fail_invalid_datetime(value):
    print(
        "error: invalid DATETIME '%s': expected format %s"
        % (value, EXPECTED_FORMAT),
        file=sys.stderr,
    )
    sys.exit(1)


def load_zone(value):
    if value != "UTC" and "/" not in value:
        print(
            "error: unknown time zone '%s': expected IANA time zone name "
            "(e.g. America/New_York, UTC)" % value,
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        print(
            "error: unknown time zone '%s': expected IANA time zone name "
            "(e.g. America/New_York, UTC)" % value,
            file=sys.stderr,
        )
        sys.exit(1)
    except (ValueError, OSError) as exc:
        print(
            "error: unavailable time zone '%s': %s" % (value, exc),
            file=sys.stderr,
        )
        sys.exit(1)


def parse_datetime(value):
    m = DATETIME_PATTERN.match(value)
    if not m:
        fail_invalid_datetime(value)
    year, month, day, hour, minute = (int(g) for g in m.groups())
    try:
        parsed = datetime(year, month, day, hour, minute)
    except ValueError:
        fail_invalid_datetime(value)
    return parsed, (year, month, day, hour, minute)


def main(argv=None):
    parser = build_parser()
    parser.add_argument(
        "datetime",
        help="date-time to convert in YYYY-MM-DD HH:MM format "
        "(e.g. 2024-01-15 12:00)",
    )
    parser.add_argument(
        "--from",
        dest="from_zone",
        required=True,
        help="source IANA time zone name (e.g. America/New_York, UTC)",
    )
    parser.add_argument(
        "--to",
        dest="to_zone",
        required=True,
        help="destination IANA time zone name (e.g. America/New_York, UTC)",
    )
    args = parser.parse_args(argv)

    dt_text = args.datetime
    src_name = args.from_zone
    dst_name = args.to_zone

    naive, _parts = parse_datetime(dt_text)
    src_zone = load_zone(src_name)
    dst_zone = load_zone(dst_name)
    try:
        utc_zone = ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        print(
            "error: missing time zone database entry for 'UTC': %s" % exc,
            file=sys.stderr,
        )
        sys.exit(1)

    dt_src = naive.replace(tzinfo=src_zone, fold=0)
    try:
        dt_utc = dt_src.astimezone(utc_zone)
    except Exception as exc:
        print(
            "error: cannot convert DATETIME '%s' from time zone '%s': %s"
            % (dt_text, src_name, exc),
            file=sys.stderr,
        )
        sys.exit(1)

    dt_back = dt_utc.astimezone(src_zone)
    if dt_back.replace(tzinfo=None) != naive:
        print(
            "error: nonexistent local time '%s' in time zone '%s': "
            "the wall time does not exist due to a daylight-saving transition"
            % (dt_text, src_name),
            file=sys.stderr,
        )
        sys.exit(1)

    dt_dst = dt_utc.astimezone(dst_zone)
    sys.stdout.write(dt_dst.strftime("%Y-%m-%d %H:%M") + "\n")
    return 0


if __name__ == "__main__":
    main()
