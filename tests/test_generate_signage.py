import unittest

from sl_emails.services.event_shapes import PosterEvent
from sl_emails.signage.generate_signage import generate_signage_html


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


if __name__ == "__main__":
    unittest.main()
