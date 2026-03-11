import unittest
from datetime import date

from sl_emails.poster.carousel import (
    PosterEvent,
    build_daily_carousel_models,
    build_daily_poster_model,
    get_week_bounds,
    normalize_custom_event,
    render_poster_fragment,
    sort_events,
)


class PosterCarouselTests(unittest.TestCase):
    def test_get_week_bounds_next_week(self):
        start, end = get_week_bounds(mode="next", today=date(2026, 3, 3))
        self.assertEqual(start.isoformat(), "2026-03-09")
        self.assertEqual(end.isoformat(), "2026-03-15")

    def test_get_week_bounds_this_week(self):
        start, end = get_week_bounds(mode="this", today=date(2026, 3, 3))
        self.assertEqual(start.isoformat(), "2026-03-02")
        self.assertEqual(end.isoformat(), "2026-03-08")

    def test_normalize_custom_event_requires_title(self):
        with self.assertRaises(ValueError):
            normalize_custom_event({"date": "2026-03-10"})

    def test_sort_events_uses_date_and_time(self):
        events = [
            PosterEvent(
                title="Late",
                subtitle="",
                date="2026-03-10",
                time="7:00 PM",
                location="",
                category="",
                source="custom",
                badge="SPECIAL",
                priority=5,
                accent="#000000",
            ),
            PosterEvent(
                title="Early",
                subtitle="",
                date="2026-03-10",
                time="3:00 PM",
                location="",
                category="",
                source="custom",
                badge="SPECIAL",
                priority=1,
                accent="#000000",
            ),
        ]

        sorted_events = sort_events(events)
        self.assertEqual(sorted_events[0].title, "Early")

    def test_build_daily_poster_model_overflow(self):
        events = [
            PosterEvent(
                title=f"Event {i}",
                subtitle="",
                date="2026-03-10",
                time="4:00 PM",
                location="Gym",
                category="Athletics",
                source="athletics",
                badge="HOME",
                priority=3,
                accent="#0C3A6B",
            )
            for i in range(20)
        ]

        model = build_daily_poster_model(
            date(2026, 3, 10),
            events,
            date(2026, 3, 9),
            date(2026, 3, 15),
            heading="This Week",
            slide_number=2,
            total_slides=7,
        )
        self.assertEqual(model["density"], "dense")
        self.assertEqual(model["overflow_count"], 6)

    def test_build_daily_carousel_models_creates_all_days(self):
        events = [
            PosterEvent(
                title="Admissions Night",
                subtitle="Prospective Families",
                date="2026-03-11",
                time="6:00 PM",
                location="Campus Center",
                category="Admissions",
                source="custom",
                badge="SPECIAL",
                priority=4,
                accent="#8C6A00",
            )
        ]

        slides = build_daily_carousel_models(events, date(2026, 3, 9), date(2026, 3, 15), heading="This Week")
        self.assertEqual(len(slides), 7)
        self.assertEqual(sum(slide["events_total"] for slide in slides), 1)
        self.assertEqual(slides[2]["events_total"], 1)

    def test_render_fragment_escapes_html(self):
        event = PosterEvent(
            title="Admissions <Night>",
            subtitle="A & B",
            date="2026-03-11",
            time="6:00 PM",
            location="Hall > South",
            category="Custom",
            source="custom",
            badge="SPECIAL",
            priority=3,
            accent="#8C6A00",
        )
        model = build_daily_poster_model(
            date(2026, 3, 11),
            [event],
            date(2026, 3, 9),
            date(2026, 3, 15),
            heading="This Week",
            slide_number=3,
            total_slides=7,
        )
        fragment = render_poster_fragment(model)

        self.assertIn("Admissions &lt;Night&gt;", fragment)
        self.assertIn("Hall &gt; South", fragment)


if __name__ == "__main__":
    unittest.main()