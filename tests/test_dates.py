import unittest
from datetime import date

from sl_emails.domain import dates


class DateHelpersTests(unittest.TestCase):
    def test_resolve_week_bounds_supports_explicit_range_and_validation(self):
        start, end = dates.resolve_week_bounds(start_date="2026-03-11", end_date="2026-03-15")

        self.assertEqual(start.isoformat(), "2026-03-09")
        self.assertEqual(end.isoformat(), "2026-03-15")

        with self.assertRaises(ValueError):
            dates.resolve_week_bounds(start_date="2026-03-11", end_date="2026-03-08")

    def test_resolve_week_bounds_supports_this_and_next_modes(self):
        today = date(2026, 3, 11)

        this_start, this_end = dates.resolve_week_bounds(mode="this", today=today)
        next_start, next_end = dates.resolve_week_bounds(mode="next", today=today)

        self.assertEqual((this_start.isoformat(), this_end.isoformat()), ("2026-03-09", "2026-03-15"))
        self.assertEqual((next_start.isoformat(), next_end.isoformat()), ("2026-03-16", "2026-03-22"))

        with self.assertRaises(ValueError):
            dates.resolve_week_bounds(mode="bad-mode", today=today)

    def test_normalize_to_iso_date_and_event_date_sort(self):
        self.assertEqual(dates.normalize_to_iso_date("Mar 17 2026"), "2026-03-17")
        self.assertEqual(dates.normalize_to_iso_date("March 17 2026"), "2026-03-17")
        self.assertEqual(dates.normalize_to_iso_date("not a date"), "not a date")

    def test_time_helpers_handle_clock_values_and_fallbacks(self):
        self.assertEqual(dates.time_for_sort("4:15 PM").strftime("%H:%M"), "16:15")
        self.assertEqual(dates.time_for_sort("4 PM").strftime("%H:%M"), "16:00")
        self.assertEqual(dates.time_for_sort("TBA").strftime("%H:%M"), "23:59")
        self.assertEqual(dates.time_sort_key("4:15 PM")[0], 16 * 60 + 15)
        self.assertEqual(dates.time_sort_key("TBA")[0], 99_999)
        self.assertEqual(dates.time_sort_key("unknown")[0], 99_998)

    def test_overlap_and_display_formatters_cover_same_month_cross_month_and_cross_year(self):
        overlaps = dates.overlap_dates("2026-03-10", "2026-03-12", "2026-03-09", "2026-03-15")
        self.assertEqual([value.isoformat() for value in overlaps], ["2026-03-10", "2026-03-11", "2026-03-12"])
        self.assertEqual(dates.overlap_dates("2026-03-01", "2026-03-02", "2026-03-09", "2026-03-15"), [])

        self.assertEqual(dates.display_date(date(2026, 3, 9)), "Mar 09 2026")
        self.assertEqual(dates.format_email_date_range("2026-03-09", "2026-03-15"), "March 9–15, 2026")
        self.assertEqual(dates.format_email_date_range("2026-03-30", "2026-04-05"), "March 30–April 05, 2026")
        self.assertEqual(dates.format_email_date_range("2026-12-30", "2027-01-05"), "December 30, 2026–January 05, 2027")
        self.assertEqual(dates.format_poster_week_label(date(2026, 3, 9), date(2026, 3, 15)), "March 9-15, 2026")
        self.assertEqual(dates.format_poster_week_label(date(2026, 3, 30), date(2026, 4, 5)), "Mar 30 - Apr 05, 2026")
        self.assertTrue(dates.format_day_long(date(2026, 3, 9)).startswith("Monday, March"))


if __name__ == "__main__":
    unittest.main()
