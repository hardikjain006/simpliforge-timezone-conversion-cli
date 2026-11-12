"""Repository-native tests for the tzconvert CLI (requirements R1-R5)."""

import os
import subprocess
import sys
import unittest

TZCONVERT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tzconvert"
)


def run_cli(*args, stdin=b""):
    """Run the CLI; return (returncode, stdout_bytes, stderr_bytes)."""
    proc = subprocess.run(
        [sys.executable, TZCONVERT, *args],
        input=stdin,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def assert_error_envelope(testcase, rc, stdout, stderr, must_contain=None):
    testcase.assertEqual(rc, 2)
    testcase.assertEqual(stdout, b"")
    testcase.assertTrue(
        stderr.startswith(b"Error: "),
        "stderr must start with 'Error: ': %r" % stderr,
    )
    testcase.assertTrue(
        stderr.endswith(b"\n") and not stderr.endswith(b"\n\n"),
        "stderr must end with a single newline: %r" % stderr,
    )
    testcase.assertEqual(
        stderr.count(b"\n"), 1, "stderr must be exactly one line: %r" % stderr
    )
    if must_contain is not None:
        testcase.assertIn(must_contain, stderr)


class TestInputMode(unittest.TestCase):
    def test_basic_shape(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T17:00 UTC\n")
        self.assertEqual(err, b"")

    def test_flag_order_insignificant(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--to", "UTC", "--from", "America/New_York"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T17:00 UTC\n")
        self.assertEqual(err, b"")

    def test_flag_equals_spelling_rejected(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from=America/New_York", "--to", "UTC"
        )
        assert_error_envelope(self, rc, out, err, must_contain=b"--from")

    def test_datetime_must_be_first(self):
        rc, out, err = run_cli(
            "--from", "America/New_York", "--to", "UTC", "2026-01-15T12:00"
        )
        assert_error_envelope(self, rc, out, err, must_contain=b"--from")

    def test_stdin_is_ignored(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "America/New_York", "--to", "UTC",
            stdin=b"2099-01-01T00:00 --from UTC --to UTC\n",
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T17:00 UTC\n")
        self.assertEqual(err, b"")


class TestDatetimeValidation(unittest.TestCase):
    BAD_DATETIMES = [
        "2026-01-15 12:00",
        "2026-01-15T12:00:00",
        "2026-1-15T12:00",
        "2026-01-15T12:00Z",
        "2026-01-15T12:00+00:00",
        "not-a-date",
        "2026-02-30T12:00",
        "2026-01-15T24:00",
        "2026-13-01T12:00",
    ]

    def test_bad_datetimes_rejected(self):
        for bad in self.BAD_DATETIMES:
            with self.subTest(datetime=bad):
                rc, out, err = run_cli(
                    bad, "--from", "America/New_York", "--to", "UTC"
                )
                assert_error_envelope(
                    self, rc, out, err, must_contain=bad.encode()
                )

    def test_leap_second_rejected(self):
        rc, out, err = run_cli(
            "2026-01-15T12:60", "--from", "UTC", "--to", "UTC"
        )
        assert_error_envelope(
            self, rc, out, err, must_contain=b"2026-01-15T12:60"
        )


class TestZones(unittest.TestCase):
    def test_unknown_source_zone(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "Mars/Olympus", "--to", "UTC"
        )
        assert_error_envelope(
            self, rc, out, err, must_contain=b"Mars/Olympus"
        )

    def test_unknown_destination_zone(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "UTC", "--to", "Mars/Olympus"
        )
        assert_error_envelope(
            self, rc, out, err, must_contain=b"Mars/Olympus"
        )

    def test_zone_names_case_sensitive(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "utc", "--to", "UTC"
        )
        assert_error_envelope(self, rc, out, err, must_contain=b"utc")


class TestOutputMode(unittest.TestCase):
    def test_documented_example(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T17:00 UTC\n")
        self.assertEqual(err, b"")
        self.assertEqual(out.count(b"\n"), 1)

    def test_reverse_conversion(self):
        rc, out, err = run_cli(
            "2026-01-15T17:00", "--from", "UTC", "--to", "America/New_York"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T12:00 America/New_York\n")
        self.assertEqual(err, b"")

    def test_summer_dst_conversion(self):
        rc, out, err = run_cli(
            "2026-07-15T12:00", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-07-15T16:00 UTC\n")
        self.assertEqual(err, b"")


class TestHelp(unittest.TestCase):
    def test_long_help(self):
        rc, out, err = run_cli("--help")
        self.assertEqual(rc, 0)
        self.assertEqual(err, b"")
        for needle in (b"DATETIME", b"--from", b"--to", b"YYYY-MM-DDTHH:MM"):
            self.assertIn(needle, out)
        lines = out.decode().splitlines()
        self.assertTrue(
            any(line.startswith("tzconvert ") for line in lines),
            "help must show a complete tzconvert example line",
        )

    def test_short_help(self):
        rc, out, err = run_cli("-h")
        self.assertEqual(rc, 0)
        self.assertEqual(err, b"")
        self.assertIn(b"DATETIME", out)

    def test_help_takes_precedence(self):
        rc, out, err = run_cli(
            "bogus", "--from", "Nope/Zone", "--to", "UTC", "--help"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(err, b"")
        self.assertIn(b"DATETIME", out)


class TestErrors(unittest.TestCase):
    def test_missing_arguments(self):
        for args in ([], ["2026-01-15T12:00"],
                      ["2026-01-15T12:00", "--from", "UTC"]):
            with self.subTest(args=args):
                rc, out, err = run_cli(*args)
                self.assertEqual(rc, 2)
                self.assertEqual(out, b"")
                self.assertTrue(err.startswith(b"Error: "))
                self.assertEqual(err.count(b"\n"), 1)

    def test_extra_argument(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00",
            "--from", "UTC", "--to", "UTC", "EXTRA",
        )
        assert_error_envelope(
            self, rc, out, err, must_contain=b"EXTRA"
        )

    def test_gap_time_rejected(self):
        rc, out, err = run_cli(
            "2026-03-08T02:30", "--from", "America/New_York", "--to", "UTC"
        )
        assert_error_envelope(
            self, rc, out, err, must_contain=b"2026-03-08T02:30"
        )

    def test_exit_codes(self):
        rc, _, _ = run_cli(
            "2026-01-15T12:00", "--from", "UTC", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        rc, _, _ = run_cli("--help")
        self.assertEqual(rc, 0)
        rc, _, _ = run_cli("bogus", "--from", "UTC", "--to", "UTC")
        self.assertEqual(rc, 2)


class TestDeterminismAndBoundaries(unittest.TestCase):
    def test_deterministic(self):
        args = ("2026-01-15T12:00", "--from", "America/New_York",
                "--to", "UTC")
        first = run_cli(*args)
        second = run_cli(*args)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 0)

    def test_fallback_overlap_uses_earlier_occurrence(self):
        rc, out, err = run_cli(
            "2025-11-02T01:30", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2025-11-02T05:30 UTC\n")
        self.assertEqual(err, b"")

    def test_same_zone_identity(self):
        rc, out, err = run_cli(
            "2026-01-15T12:00", "--from", "UTC", "--to", "UTC"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"2026-01-15T12:00 UTC\n")
        self.assertEqual(err, b"")


if __name__ == "__main__":
    unittest.main()
