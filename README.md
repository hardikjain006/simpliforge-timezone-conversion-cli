# Timezone-conversion CLI — Requirements

Goal: convert one date-time from one IANA time zone to another, with one
input mode, one output mode, useful help text, and predictable errors.

## 1. Invocation

- The program is a file named `tzconvert.py` at the repository root.
- It runs as `python3 tzconvert.py DATETIME --from SRC_TZ --to DST_TZ`.
- It MUST run on Python 3 with only the standard library (no third-party
  installs). Time-zone data comes from the standard-library `zoneinfo`
  database available in the runtime.

## 2. Arguments

- `DATETIME` (required, positional): the date-time to convert, in the single
  input format defined in section 3.
- `--from SRC_TZ` (required): IANA name of the source zone
  (e.g. `America/New_York`, `UTC`). Case-sensitive.
- `--to DST_TZ` (required): IANA name of the destination zone. Case-sensitive.
- `--help` / `-h` (optional): print help text per section 6 and exit 0.
  No other flags, subcommands, or interactive/stdin modes exist.

## 3. Input mode (exactly one)

- `DATETIME` MUST match `YYYY-MM-DD HH:MM` exactly: four-digit year,
  two-digit month, day, hour (00–23), and minute (00–59), zero-padded, with a
  single space separator, e.g. `2024-01-15 12:00`.
- The value MUST be a real calendar date-time (month 01–12, day valid for the
  month including leap years, hour 00–23, minute 00–59).
- The value carries no seconds, no `T` separator, no UTC offset, and no zone
  suffix. Any of those is malformed input.
- `SRC_TZ` and `DST_TZ` MUST each be a valid IANA key loadable via
  `zoneinfo` (including `UTC`). Unknown, empty, or misspelled names are
  invalid. Zone abbreviations (e.g. `EST`) and fixed offsets (e.g. `+05:00`)
  are NOT accepted as zone arguments.
- `DATETIME` is interpreted as wall time in `SRC_TZ`.

## 4. Conversion semantics

- The program maps the input wall time in `SRC_TZ` to the same instant and
  renders that instant as wall time in `DST_TZ`.
- Nonexistent local times (spring-forward gaps, e.g. `2024-03-10 02:30` in
  `America/New_York`) are errors per section 7, never silently shifted.
- Ambiguous local times (fall-back overlaps, e.g. `2024-11-03 01:30` in
  `America/New_York`) resolve deterministically to the earlier occurrence
  (`fold=0`).
- Conversion is a pure function of the command-line arguments: no network,
  no current-time, no locale, and no environment dependence. Identical
  invocations always produce identical bytes.

## 5. Output mode (exactly one)

- On success the program prints exactly one line to stdout:
  `<YYYY-MM-DD HH:MM>\n`, the converted wall time in `DST_TZ` in the same
  zero-padded format, with a single trailing newline and no other text.
- On success stderr MUST be empty and the exit status MUST be 0.
- On any failure stdout MUST be empty (no partial result).

## 6. Help text

- `python3 tzconvert.py --help` (and `-h`) MUST exit 0 and print to stdout:
  - a usage line showing
    `python3 tzconvert.py DATETIME --from SRC_TZ --to DST_TZ`;
  - what each argument means, including the exact `YYYY-MM-DD HH:MM` format;
  - that zones are IANA names (with at least two examples such as
    `America/New_York` and `UTC`);
  - at least one full example invocation with its expected output.

## 7. Predictable errors

All failures exit non-zero with the cause on stderr and nothing on stdout:

| Condition | Exit | Stderr |
|---|---|---|
| Missing/extra args, unknown flags | 2 | usage plus cause |
| Malformed `DATETIME` (wrong shape or impossible date/time) | 1 | names the value, states `YYYY-MM-DD HH:MM` |
| Unknown `SRC_TZ` / `DST_TZ` | 1 | names the value, states IANA zones expected |
| Nonexistent wall time (DST gap) | 1 | names the value and zone |
| Missing tz database entry at runtime | 1 | names the zone |

- Every value-error message MUST name the offending value and the expected
  shape; usage errors MUST print usage.
- `--help` MUST NOT be treated as an error.

## 8. Boundary cases that MUST hold

- Leap day: `2024-02-29 12:00` UTC converts normally; `2023-02-29 12:00` is
  malformed (2023 is not a leap year).
- Day rollover: `2024-01-15 12:00 --from America/New_York --to Asia/Tokyo`
  yields the next calendar day (`2024-01-16 02:00`).
- DST-aware offsets: `2024-01-15 12:00` (`EST`, UTC−5) and
  `2024-07-15 12:00` (`EDT`, UTC−4) in `America/New_York` convert to
  `2024-01-15 17:00` and `2024-07-15 16:00` in `UTC` respectively.
- Same-zone conversion (`--from X --to X`) echoes the input value.
- `UTC` is a valid zone on either side.

## 9. Non-goals

- No stdin, file, batch, config-file, or multiple-format modes.
- No seconds, sub-minute precision, alternate separators, or embedded offsets.
- No zone listing, fuzzy matching, abbreviations, or offset arguments.
- No logging, color, progress, or extra output channels.

## 10. Acceptance check (examples)

- `python3 tzconvert.py "2024-01-15 12:00" --from America/New_York --to UTC`
  → stdout `2024-01-15 17:00`, exit 0.
- `python3 tzconvert.py "2024-01-15 12:00" --from UTC --to Asia/Tokyo`
  → stdout `2024-01-15 21:00`, exit 0.
- `python3 tzconvert.py "2024-03-10 02:30" --from America/New_York --to UTC`
  → exit 1, stderr names the value, stdout empty.
- `python3 tzconvert.py "not-a-date" --from UTC --to UTC`
  → exit 1, stderr states the expected format, stdout empty.
- `python3 tzconvert.py --help` → exit 0, stdout contains usage and an example.
