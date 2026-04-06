import unittest
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sl_emails.services.event_shapes import PosterEvent
from sl_emails.signage.generate_signage import (
    _coerce_display_date,
    audience_label,
    categorize_events,
    event_badge_style,
    event_card_html,
    event_detail,
    event_display_config,
    event_summary,
    event_title,
    fetch_events_for_date,
    generate_signage_html,
    get_date_range,
    hex_to_rgba,
    layout_plan,
    main,
    normalized_hex,
    source_counts,
    source_label,
    summary_pills_html,
)


class GenerateSignageHtmlTests(unittest.TestCase):
    def test_generate_signage_html_renders_empty_state(self):
        html = generate_signage_html([], "2026-03-23")

        self.assertIn("Kent Denver Digital Signage", html)
        self.assertIn("No Events Today", html)
        self.assertIn("The daily board is clear for now.", html)
        self.assertNotIn("Designed like the new email system", html)

    def test_generate_signage_html_uses_spotlight_layout_and_escapes_copy(self):
        events = [
            PosterEvent(
                title="Varsity Soccer <Elite>",
                subtitle="vs. Front Range & Co",
                date="2026-03-23",
                time="4:00 PM",
                location="Main Field <West>",
                category="Soccer",
                source="athletics",
                badge="HOME",
                priority=4,
                accent="#0066ff",
                audiences=["upper-school"],
                team="Varsity Soccer <Elite>",
                opponent="Front Range & Co",
                is_home=True,
                metadata={"source_type": "game", "sport": "soccer"},
            ),
            PosterEvent(
                title="Spring Concert & Showcase",
                subtitle="Music",
                date="2026-03-23",
                time="7:00 PM",
                location="Performing Arts Center",
                category="Music",
                source="arts",
                badge="EVENT",
                priority=4,
                accent="#A11919",
                audiences=["middle-school", "upper-school"],
                team="Spring Concert & Showcase",
                metadata={"source_type": "arts"},
            ),
        ]

        html = generate_signage_html(events, "2026-03-23")

        self.assertIn('class="board-layout"', html)
        self.assertIn('--row-columns: 2;', html)
        self.assertIn('data-density="spotlight"', html)
        self.assertIn("Varsity Soccer &lt;Elite&gt;", html)
        self.assertIn("Front Range &amp; Co", html)
        self.assertIn("Main Field &lt;West&gt;", html)
        self.assertNotIn("Designed like the new email system", html)

    def test_generate_signage_html_uses_two_three_column_rows_for_six_events(self):
        events = [
            PosterEvent(
                title=f"Event {index}",
                subtitle=f"Subtitle {index}",
                date="2026-03-23",
                time=f"{index + 1}:00 PM",
                location=f"Location {index}",
                category="Soccer" if index % 2 == 0 else "Music",
                source="athletics" if index % 2 == 0 else "arts",
                badge="HOME" if index % 2 == 0 else "EVENT",
                priority=4 if index < 2 else 3,
                accent="#0066ff" if index % 2 == 0 else "#A11919",
                audiences=["upper-school"],
                team=f"Team {index}",
                opponent=f"Opponent {index}",
                is_home=True,
                metadata={"source_type": "game" if index % 2 == 0 else "arts"},
            )
            for index in range(6)
        ]

        html = generate_signage_html(events, "2026-03-23")

        self.assertEqual(html.count('class="board-row"'), 2)
        self.assertEqual(html.count("--row-columns: 3;"), 2)
        self.assertIn('data-density="compact"', html)

    def test_generate_signage_html_uses_four_three_split_for_seven_events(self):
        events = [
            PosterEvent(
                title=f"Event {index}",
                subtitle=f"Subtitle {index}",
                date="2026-03-23",
                time=f"{index + 1}:00 PM",
                location=f"Location {index}",
                category="Soccer",
                source="athletics",
                badge="HOME",
                priority=3,
                accent="#0066ff",
                audiences=["upper-school"],
                team=f"Team {index}",
                opponent=f"Opponent {index}",
                is_home=True,
                metadata={"source_type": "game"},
            )
            for index in range(7)
        ]

        html = generate_signage_html(events, "2026-03-23")

        self.assertEqual(html.count('class="board-row"'), 2)
        self.assertIn("--row-columns: 4;", html)
        self.assertIn("--row-columns: 3;", html)
        self.assertIn('data-density="dense"', html)

    def test_helper_functions_cover_event_labels_counts_and_colors(self):
        athletics = PosterEvent(
            title="Varsity Soccer",
            subtitle="Quarterfinal",
            date="2026-03-23",
            time="4:00 PM",
            location="Main Field",
            category="Soccer",
            source="athletics",
            badge="AWAY",
            priority=3,
            accent="bad-color",
            audiences=["upper-school"],
            team="Varsity Soccer",
            opponent="Front Range",
            is_home=False,
            metadata={},
        )
        arts = PosterEvent(
            title="Spring Play",
            subtitle="Opening Night",
            date="2026-03-23",
            time="7:00 PM",
            location="Theater",
            category="Theater",
            source="arts",
            badge="EVENT",
            priority=4,
            accent="#a11919",
            audiences=["middle-school", "upper-school"],
            team="Spring Play",
            metadata={},
        )
        custom = PosterEvent(
            title="Community Lunch",
            subtitle="",
            date="2026-03-23",
            time="",
            location="",
            category="Community",
            source="custom",
            badge="",
            priority=2,
            accent="",
            audiences=["middle-school"],
            metadata={},
        )

        featured, regular = categorize_events([custom, athletics, arts])
        self.assertEqual([event.title for event in featured], ["Varsity Soccer", "Spring Play"])
        self.assertEqual([event.title for event in regular], ["Community Lunch"])
        self.assertEqual(source_counts([athletics, arts, custom]), {"athletics": 1, "arts": 1, "custom": 1, "total": 3})
        self.assertEqual(normalized_hex("#a11919"), "#A11919")
        self.assertEqual(normalized_hex("bad-color"), "#041E42")
        self.assertEqual(hex_to_rgba("#A11919", 0.2), "rgba(161, 25, 25, 0.200)")
        self.assertEqual(audience_label(["middle-school", "upper-school"]), "All School")
        self.assertEqual(audience_label(["middle-school"]), "Middle School")
        self.assertEqual(source_label(athletics), "Athletics")
        self.assertEqual(source_label(arts), "Arts")
        self.assertEqual(source_label(custom), "School Event")
        self.assertEqual(event_title(athletics), "Varsity Soccer")
        self.assertEqual(event_title(custom), "Community Lunch")
        self.assertEqual(event_summary(athletics), "vs. Front Range")
        self.assertEqual(event_summary(custom), "Community")
        self.assertEqual(event_detail(athletics), "Main Field")
        self.assertEqual(event_detail(custom), "On Campus")
        self.assertIn("School Events", summary_pills_html([athletics, arts, custom]))
        self.assertEqual(event_display_config(athletics)["icon"], "soccer")
        self.assertEqual(event_badge_style(athletics)["text"], "Away")
        self.assertEqual(event_badge_style(arts)["text"], "Event")

    def test_layout_card_and_date_helpers_cover_dense_and_default_paths(self):
        self.assertEqual(layout_plan(3), {"rows": [3], "density": "cozy"})
        self.assertEqual(layout_plan(10), {"rows": [5, 5], "density": "dense"})
        self.assertEqual(layout_plan(11), {"rows": [5, 5, 1], "density": "dense"})

        event = PosterEvent(
            title="Advisory",
            subtitle="",
            date="2026-03-23",
            time="",
            location="",
            category="Advisory",
            source="custom",
            badge="",
            priority=2,
            accent="",
            audiences=["middle-school"],
            metadata={},
        )
        card = event_card_html(event, density="mystery")
        self.assertIn("Middle School", card)
        self.assertIn("Start", card)
        self.assertIn("TBA", card)
        self.assertIn("--accent: #6B7280;", card)

        coerced_from_string = _coerce_display_date("2026-03-23")
        coerced_from_date = _coerce_display_date(date(2026, 3, 24))
        self.assertEqual(coerced_from_string.strftime("%Y-%m-%d"), "2026-03-23")
        self.assertEqual(coerced_from_date.strftime("%Y-%m-%d"), "2026-03-24")
        self.assertIsInstance(_coerce_display_date(datetime(2026, 3, 25, 8, 0)), datetime)

    def test_fetch_and_cli_entrypoint_cover_console_paths(self):
        with patch("sl_emails.signage.generate_signage.fetch_signage_events", return_value=[]):
            events, target_day = fetch_events_for_date("2026-03-23")
        self.assertEqual(events, [])
        self.assertEqual(target_day.isoformat(), "2026-03-23")

        with patch("sys.stdout", new_callable=StringIO) as stdout:
            with self.assertRaises(SystemExit):
                get_date_range("bad-date")
        self.assertIn("Invalid date format", stdout.getvalue())

        with TemporaryDirectory() as tempdir:
            output_path = Path(tempdir) / "digital-signage" / "index.html"
            with (
                patch("sl_emails.signage.generate_signage.fetch_events_for_date", return_value=([], date(2026, 3, 23))),
                patch("sl_emails.signage.generate_signage.generate_signage_html", return_value="<html>ok</html>"),
                patch("sl_emails.signage.generate_signage.SIGNAGE_OUTPUT_HTML", output_path),
                patch("sys.argv", ["generate_signage.py", "--date", "2026-03-23"]),
            ):
                main()

            self.assertEqual(output_path.read_text(encoding="utf-8"), "<html>ok</html>")


if __name__ == "__main__":
    unittest.main()
