# Timezone-conversion CLI

## Goal

Build a "Timezone-conversion CLI" with one input mode, one output mode,
useful help text, and predictable errors.

## Requirements contract

This section is the complete public requirements contract for the goal. A
developer can implement and test the CLI from this file alone.

### R1 — Single input mode (command-line arguments only)

- R1.1: The CLI accepts all conversion inputs exclusively as command-line
  arguments. There is exactly one supported invocation shape:
  `tzconvert DATETIME --from SRC_TZ --to DST_TZ`, with `DATETIME` as the
  first argument. `--from` and `--to` may appear in either order after
  `DATETIME`. Only the space-separated spelling (`--from SRC_TZ`) is
  accepted; the `--flag=value` spelling (e.g. `--from=UTC`) is an
  extra/misplaced-argument error under R4.2.
- R1.2: `DATETIME` is a single argument in exactly one accepted format:
  `YYYY-MM-DDTHH:MM` (24-hour clock, zero-padded, e.g. `2026-01-15T12:00`).
  It denotes the wall-clock time in `SRC_TZ`, with no embedded offset or
  zone suffix.
- R1.3: `SRC_TZ` and `DST_TZ` are IANA time-zone names (e.g.
  `America/New_York`, `UTC`), matched case-sensitively.
- R1.4: No other input mode is supported: not stdin, files, environment
  variables, interactive prompts, or extra subcommands/flags that supply
  conversion inputs. Unsupported input mechanisms must not silently alter
  the result.

### R2 — Single output mode (one line on stdout)

- R2.1: On success the CLI writes exactly one line to stdout and nothing
  else to stdout: the converted wall-clock time in `DST_TZ`, formatted as
  `YYYY-MM-DDTHH:MM DST_TZ` (e.g. `2026-01-15T17:00 UTC`), followed by a
  single trailing newline. On success it writes nothing to stderr.
- R2.2: No other output mode is supported: no JSON, files, verbose, quiet,
  or multi-line formats.
- R2.3: Example: `tzconvert 2026-01-15T12:00 --from America/New_York --to
  UTC` writes `2026-01-15T17:00 UTC` to stdout.

### R3 — Help text

- R3.1: `tzconvert --help` (and `-h`) prints useful help text to stdout,
  writes nothing to stderr, and exits with status 0, without requiring any
  other arguments. `--help`/`-h` takes precedence whenever present: the CLI
  prints help, exits 0, performs no conversion, and ignores any
  accompanying conversion arguments.
- R3.2: The help text states the invocation shape, describes `DATETIME`,
  `--from`, and `--to`, and shows at least one complete example. A
  conformance test asserts only these literal inclusions: the help output
  contains the substrings `DATETIME`, `--from`, `--to`, and
  `YYYY-MM-DDTHH:MM`, plus one line containing a complete `tzconvert`
  example invocation starting with the literal `tzconvert`.

### R4 — Predictable errors

- R4.1: Every failure caused by caller input exits with status 2, writes
  exactly one line to stderr in the shape `Error: <reason>` (a single
  trailing newline), and writes nothing to stdout. Where the failure names
  a specific value or option, `<reason>` must contain that offending value
  or option name verbatim (e.g. the bad zone string, the bad `DATETIME`
  string, or `--from`/`--to`). Conformance tests assert the exit-2 /
  single-line / `Error: ` envelope, empty stdout, and that inclusion — not
  any exact full message.
- R4.2: The following inputs are errors under R4.1: missing or extra
  arguments; a `DATETIME` that does not match `YYYY-MM-DDTHH:MM` or is not
  a real calendar time; an unknown `SRC_TZ` or `DST_TZ`; a wall-clock time
  that never occurs in `SRC_TZ` (e.g. inside a DST spring-forward gap).
- R4.3: Exit status 0 is reserved for success (R2) and help (R3). Status 2
  is used for every input error. No input error exits 0.

### R5 — Determinism and boundary cases

- R5.1: Conversion is a pure function of the three arguments: identical
  invocations produce byte-identical stdout, with no dependence on the
  machine clock, locale, or network.
- R5.2: A wall-clock time that occurs twice in `SRC_TZ` (DST fall-back
  overlap) resolves deterministically to the earlier occurrence and
  converts normally; it is not an error.
- R5.3: Converting a zone to itself outputs the same wall-clock time with
  that zone's name (e.g. input `...T12:00 --from UTC --to UTC` outputs
  `...T12:00 UTC`).
- R5.4: Leap seconds, if present in an input, are rejected as invalid
  datetimes under R4.2 (`MM` ranges over `00`–`59`).

## Non-goals

- No additional input or output modes, configuration files, or
  long-running/server behavior.
- No prescription of implementation language, libraries, or packaging;
  any implementation satisfying R1–R5 is acceptable.
