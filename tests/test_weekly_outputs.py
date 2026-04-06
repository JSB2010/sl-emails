import unittest

from sl_emails.domain.weekly import WeeklyDraftRecord, WeeklyEventRecord, default_copy_overrides, default_delivery_state
from sl_emails.services.weekly_outputs import (
    build_weekly_email_outputs,
    default_subject_for_date_range,
    extract_subject,
    renderable_events_for_audience,
)


class _FakeGenerateGamesModule:
    class Game:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.event_type = "game"

    class Event:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.event_type = "arts" if kwargs.get("category") == "Music" else "event"

    @staticmethod
    def format_date_range(start_date, end_date):
        return f"{start_date} - {end_date}"

    @staticmethod
    def group_games_by_date(items):
        grouped = {}
        for item in items:
            grouped.setdefault(item.date, []).append(item)
        return grouped

    @staticmethod
    def generate_html_email(grouped, date_range, sports_list, start_date, end_date, school_level, **kwargs):
        rendered_titles = []
        for items in grouped.values():
            rendered_titles.extend(getattr(item, "team", "") or getattr(item, "title", "") for item in items)
        title = kwargs.get("email_subject") or "Untitled"
        has_arts = "true" if "Music" in sports_list else "false"
        return (
            f'<html><head><meta name="has-arts-events" content="{has_arts}"><title>{title} ({date_range})</title></head>'
            f"<body>{school_level}|{sports_list}|{'|'.join(rendered_titles)}|{kwargs.get('icon_base_url', '')}</body></html>"
        )


class WeeklyOutputsTests(unittest.TestCase):
    def _sample_week(self):
        return WeeklyDraftRecord(
            week_id="2026-03-09",
            start_date="2026-03-09",
            end_date="2026-03-15",
            heading="Championship Week",
            notes="Bring the whole family.",
            subject_overrides={"middle-school": "Middle School Highlights"},
            delivery=default_delivery_state("2026-03-09"),
            copy_overrides=default_copy_overrides(),
            events=[
                WeeklyEventRecord(
                    id="multi-day-event",
                    title="Arts Festival",
                    start_date="2026-03-10",
                    end_date="2026-03-12",
                    time_text="6:00 PM",
                    location="PAC",
                    category="Music",
                    source="arts",
                    audiences=["middle-school", "upper-school"],
                    kind="event",
                    team="Arts Festival",
                ),
                WeeklyEventRecord(
                    id="game-1",
                    title="Varsity Soccer",
                    start_date="2026-03-11",
                    end_date="2026-03-11",
                    time_text="4:00 PM",
                    location="Main Field",
                    category="Soccer",
                    source="athletics",
                    audiences=["upper-school"],
                    kind="game",
                    team="Varsity Soccer",
                    opponent="Front Range",
                    is_home=True,
                ),
                WeeklyEventRecord(
                    id="hidden-event",
                    title="Hidden Internal Note",
                    start_date="2026-03-11",
                    end_date="2026-03-11",
                    time_text="TBA",
                    location="Campus",
                    category="Community",
                    source="custom",
                    audiences=["middle-school", "upper-school"],
                    kind="event",
                    status="hidden",
                    team="Hidden Internal Note",
                ),
            ],
        )

    def test_renderable_events_for_audience_filters_hidden_and_expands_multi_day_events(self):
        week = self._sample_week()

        middle_school = renderable_events_for_audience(
            week,
            "middle-school",
            generate_games_module=_FakeGenerateGamesModule,
        )
        upper_school = renderable_events_for_audience(
            week,
            "upper-school",
            generate_games_module=_FakeGenerateGamesModule,
        )

        self.assertEqual(len(middle_school), 3)
        self.assertEqual(len(upper_school), 4)
        self.assertTrue(all("Hidden Internal Note" not in getattr(item, "title", "") for item in middle_school))
        self.assertEqual([item.date for item in middle_school], ["Mar 10 2026", "Mar 11 2026", "Mar 12 2026"])

    def test_subject_helpers_cover_default_and_html_extraction(self):
        self.assertEqual(
            default_subject_for_date_range("March 9–15, 2026", has_arts=False),
            "Sports This Week: March 9 - 15",
        )
        self.assertEqual(
            default_subject_for_date_range("March 9–15, 2026", has_arts=True),
            "Sports and Performances This Week: March 9 - 15",
        )
        self.assertEqual(
            extract_subject('<html><head><meta name="has-arts-events" content="true"><title>Weekly Update (March 9–15, 2026)</title></head></html>'),
            "Sports and Performances This Week: March 9 - 15",
        )
        self.assertEqual(
            extract_subject("<html><head><title>Plain Title</title></head></html>"),
            "Plain Title",
        )

    def test_build_weekly_email_outputs_counts_occurrences_and_applies_overrides(self):
        outputs = build_weekly_email_outputs(
            self._sample_week(),
            generate_games_module=_FakeGenerateGamesModule,
            icon_base_url="https://assets.example.test",
        )

        self.assertEqual(outputs["middle-school"]["subject"], "Middle School Highlights")
        self.assertEqual(outputs["upper-school"]["default_subject"], "Sports and Performances This Week: 2026-03-09 - 2026-03-15")
        self.assertEqual(outputs["middle-school"]["source_event_count"], 1)
        self.assertEqual(outputs["middle-school"]["rendered_occurrence_count"], 3)
        self.assertEqual(outputs["upper-school"]["source_event_count"], 2)
        self.assertEqual(outputs["upper-school"]["rendered_occurrence_count"], 4)
        self.assertIn("https://assets.example.test", outputs["upper-school"]["html"])
        self.assertIn("Varsity Soccer", outputs["upper-school"]["html"])


if __name__ == "__main__":
    unittest.main()
