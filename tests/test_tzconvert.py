"""Black-box tests for the public timezone-conversion CLI contract.

Every test drives the CLI in a child process and asserts only publicly
observable behavior (arguments, output streams, exit status, files).
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path


def _repo_root():
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, here.parent, Path("/app")):
        if (candidate / "tzconvert.py").is_file():
            return candidate
    return here.parent.parent


ROOT = _repo_root()
TZCONVERT = str(ROOT / "tzconvert.py")
PYTHON = sys.executable


def run_cli(*argv):
    return subprocess.run(
        [PYTHON, TZCONVERT, *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class TestSuccessConversions(unittest.TestCase):
    def test_acceptance_winter_est_to_utc(self):
        p = run_cli("2024-01-15 12:00", "--from", "America/New_York", "--to", "UTC")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-01-15 17:00\n")
        self.assertEqual(p.stderr, "")

    def test_acceptance_utc_to_tokyo(self):
        p = run_cli("2024-01-15 12:00", "--from", "UTC", "--to", "Asia/Tokyo")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-01-15 21:00\n")
        self.assertEqual(p.stderr, "")

    def test_day_rollover(self):
        p = run_cli(
            "2024-01-15 12:00", "--from", "America/New_York", "--to", "Asia/Tokyo"
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-01-16 02:00\n")
        self.assertEqual(p.stderr, "")

    def test_dst_winter_offset(self):
        p = run_cli("2024-01-15 12:00", "--from", "America/New_York", "--to", "UTC")
        self.assertEqual(p.stdout, "2024-01-15 17:00\n")

    def test_dst_summer_offset(self):
        p = run_cli("2024-07-15 12:00", "--from", "America/New_York", "--to", "UTC")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-07-15 16:00\n")
        self.assertEqual(p.stderr, "")

    def test_same_zone_echo(self):
        for zone in ("UTC", "America/New_York", "Asia/Tokyo"):
            with self.subTest(zone=zone):
                p = run_cli("2024-01-15 12:00", "--from", zone, "--to", zone)
                self.assertEqual(p.returncode, 0)
                self.assertEqual(p.stdout, "2024-01-15 12:00\n")
                self.assertEqual(p.stderr, "")

    def test_utc_both_sides(self):
        p = run_cli("2024-06-01 00:00", "--from", "UTC", "--to", "UTC")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-06-01 00:00\n")

    def test_leap_day_valid(self):
        p = run_cli("2024-02-29 12:00", "--from", "UTC", "--to", "UTC")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-02-29 12:00\n")
        self.assertEqual(p.stderr, "")

    def test_ambiguous_resolves_to_earlier(self):
        # 2024-11-03 01:30 in America/New_York happens twice; the earlier
        # (EDT, UTC-4) maps to 05:30 UTC.
        p = run_cli(
            "2024-11-03 01:30", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-11-03 05:30\n")
        self.assertEqual(p.stderr, "")

    def test_post_gap_time_succeeds(self):
        p = run_cli(
            "2024-03-10 03:30", "--from", "America/New_York", "--to", "UTC"
        )
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "2024-03-10 07:30\n")
        self.assertEqual(p.stderr, "")

    def test_deterministic_bytes(self):
        args = ("2024-01-15 12:00", "--from", "America/New_York", "--to", "UTC")
        first = run_cli(*args)
        second = run_cli(*args)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout.encode("utf-8"), b"2024-01-15 17:00\n")


class TestOutputMode(unittest.TestCase):
    def test_exactly_one_line_with_newline(self):
        p = run_cli("2024-01-15 12:00", "--from", "UTC", "--to", "Asia/Tokyo")
        self.assertEqual(p.returncode, 0)
        self.assertTrue(p.stdout.endswith("\n"))
        self.assertEqual(p.stdout.count("\n"), 1)
        self.assertRegex(p.stdout, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\n$")
        self.assertEqual(p.stderr, "")

    def test_no_extra_text(self):
        p = run_cli("2024-01-15 12:00", "--from", "America/New_York", "--to", "UTC")
        self.assertEqual(p.stdout, "2024-01-15 17:00\n")


class TestHelp(unittest.TestCase):
    def _assert_help_contract(self, p):
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stderr, "")
        body = p.stdout
        self.assertIn("python3 tzconvert.py DATETIME --from SRC_TZ --to DST_TZ", body)
        self.assertIn("YYYY-MM-DD HH:MM", body)
        self.assertIn("IANA", body)
        self.assertIn("America/New_York", body)
        self.assertIn("UTC", body)
        # At least one full example invocation with its expected output.
        self.assertIn("python3 tzconvert.py", body)
        self.assertIn("--from", body)
        self.assertIn("--to", body)
        self.assertRegex(body, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

    def test_long_help(self):
        self._assert_help_contract(run_cli("--help"))

    def test_short_help(self):
        self._assert_help_contract(run_cli("-h"))


class TestMalformedDatetime(unittest.TestCase):
    BAD_VALUES = [
        "not-a-date",
        "2024-01-15",
        "12:00",
        "",
        "2024-01-15T12:00",
        "2024-01-15 12:00:00",
        "2024-01-15 12:00+00:00",
        "2024-01-15 12:00 UTC",
        "2024-13-15 12:00",
        "2024-00-15 12:00",
        "2024-01-32 12:00",
        "2024-01-00 12:00",
        "2024-02-30 12:00",
        "2023-02-29 12:00",
        "2024-01-15 24:00",
        "2024-01-15 12:60",
        "2024-1-15 12:00",
        "2024-01-5 12:00",
        "2024-01-15 2:00",
        "2024-01-15 12:0",
        "24-01-15 12:00",
        "2024/01/15 12:00",
        "2024-01-15  12:00",
        "2024-01-15 12:00 ",
        " 2024-01-15 12:00",
    ]

    def test_each_bad_datetime_is_exit_1_with_format(self):
        for value in self.BAD_VALUES:
            with self.subTest(value=value):
                p = run_cli(value, "--from", "UTC", "--to", "UTC")
                self.assertEqual(p.returncode, 1, msg=value)
                self.assertEqual(p.stdout, "", msg=value)
                self.assertIn(value, p.stderr, msg=value)
                self.assertIn("YYYY-MM-DD HH:MM", p.stderr, msg=value)


class TestUnknownZones(unittest.TestCase):
    BAD_ZONES = [
        "No/Such_Zone",
        "EST",
        "+05:00",
        "",
        "america/New_York",
        "utc",
        "americas/new_york",
    ]

    def test_bad_src_zone(self):
        for zone in self.BAD_ZONES:
            with self.subTest(zone=zone):
                p = run_cli("2024-01-15 12:00", "--from", zone, "--to", "UTC")
                self.assertEqual(p.returncode, 1, msg=zone)
                self.assertEqual(p.stdout, "", msg=zone)
                self.assertIn(zone, p.stderr, msg=zone)
                self.assertIn("IANA", p.stderr, msg=zone)

    def test_bad_dst_zone(self):
        for zone in self.BAD_ZONES:
            with self.subTest(zone=zone):
                p = run_cli("2024-01-15 12:00", "--from", "UTC", "--to", zone)
                self.assertEqual(p.returncode, 1, msg=zone)
                self.assertEqual(p.stdout, "", msg=zone)
                self.assertIn(zone, p.stderr, msg=zone)
                self.assertIn("IANA", p.stderr, msg=zone)


class TestNonexistentWallTime(unittest.TestCase):
    def test_spring_forward_gap_fails(self):
        value = "2024-03-10 02:30"
        zone = "America/New_York"
        p = run_cli(value, "--from", zone, "--to", "UTC")
        self.assertEqual(p.returncode, 1)
        self.assertEqual(p.stdout, "")
        self.assertIn(value, p.stderr)
        self.assertIn(zone, p.stderr)

    def test_gap_start_also_fails(self):
        value = "2024-03-10 02:00"
        zone = "America/New_York"
        p = run_cli(value, "--from", zone, "--to", "UTC")
        self.assertEqual(p.returncode, 1)
        self.assertEqual(p.stdout, "")
        self.assertIn(value, p.stderr)
        self.assertIn(zone, p.stderr)


class TestUsageErrors(unittest.TestCase):
    def _assert_usage_error(self, p):
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, "")
        combined = p.stderr
        self.assertIn("usage", combined.lower())
        self.assertIn("python3 tzconvert.py", combined)

    def test_missing_datetime(self):
        self._assert_usage_error(run_cli("--from", "UTC", "--to", "UTC"))

    def test_missing_from(self):
        self._assert_usage_error(run_cli("2024-01-15 12:00", "--to", "UTC"))

    def test_missing_to(self):
        self._assert_usage_error(run_cli("2024-01-15 12:00", "--from", "UTC"))

    def test_missing_all(self):
        self._assert_usage_error(run_cli())

    def test_extra_positional(self):
        self._assert_usage_error(
            run_cli(
                "2024-01-15 12:00",
                "extra",
                "--from",
                "UTC",
                "--to",
                "UTC",
            )
        )

    def test_unknown_flag(self):
        self._assert_usage_error(
            run_cli(
                "2024-01-15 12:00", "--from", "UTC", "--to", "UTC", "--bogus"
            )
        )


if __name__ == "__main__":
    unittest.main()
