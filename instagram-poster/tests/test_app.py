import sys
import unittest
from pathlib import Path
from unittest.mock import patch

THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

import app as app_module  # noqa: E402
from poster_generator import PosterEvent  # noqa: E402


class AppApiTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_render_endpoint_handles_custom_event(self):
        response = self.client.post(
            "/api/render",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "This Week",
                "base_events": [],
                "custom_events": [
                    {
                        "title": "Robotics Night",
                        "date": "2026-03-10",
                        "time": "6:00 PM",
                        "location": "Innovation Lab",
                        "category": "STEM",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["slide_count"], 7)
        self.assertEqual(sum(slide["events_total"] for slide in payload["slides"]), 1)
        self.assertIn("Robotics Night", payload["slides"][1]["poster_html"])

    @patch.object(app_module, "fetch_week_events")
    def test_fetch_events_endpoint(self, mock_fetch):
        mock_fetch.return_value = [
            PosterEvent(
                title="Sample",
                subtitle="vs. Opp",
                date="2026-03-09",
                time="4:00 PM",
                location="Gym",
                category="Basketball",
                source="athletics",
                badge="HOME",
                priority=3,
                accent="#0C3A6B",
            )
        ]

        response = self.client.post(
            "/api/fetch-events",
            json={"mode": "custom", "start_date": "2026-03-09", "end_date": "2026-03-15"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["title"], "Sample")


if __name__ == "__main__":
    unittest.main()
