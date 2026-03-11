import unittest
from datetime import date

from sl_emails.domain.dates import resolve_week_bounds
from sl_emails.services.event_shapes import normalize_custom_event, source_event_to_poster_event


class _FakeGame:
    event_type = "game"

    def __init__(self):
        self.team = "Middle School Volleyball"
        self.opponent = "Front Range"
        self.date = "Mar 10 2026"
        self.time = "4:00 PM"
        self.location = "Kent Denver Gym"
        self.is_home = True
        self.sport = "volleyball"


class SharedEventShapeTests(unittest.TestCase):
    def test_resolve_week_bounds_next_week(self):
        start, end = resolve_week_bounds(mode="next", today=date(2026, 3, 3))

        self.assertEqual(start.isoformat(), "2026-03-09")
        self.assertEqual(end.isoformat(), "2026-03-15")

    def test_normalize_custom_event_rejects_non_iso_dates(self):
        with self.assertRaises(ValueError):
            normalize_custom_event({"title": "Robotics Night", "date": "Mar 10 2026"})

    def test_source_event_to_poster_event_preserves_legacy_fields(self):
        event = source_event_to_poster_event(_FakeGame(), lambda team: "varsity" in team.lower())

        self.assertEqual(event.date, "2026-03-10")
        self.assertEqual(event.badge, "HOME")
        self.assertEqual(event.priority, 3)
        self.assertEqual(event.accent, "#F59E0B")


if __name__ == "__main__":
    unittest.main()