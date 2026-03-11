import unittest

from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app


class EmailsAdminUiTests(unittest.TestCase):
    def setUp(self):
        app = create_app({"TESTING": True, "EMAILS_STORE": MemoryWeeklyEmailStore()})
        self.client = app.test_client()

    def test_emails_page_exposes_dashboard_filters(self):
        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Filter large weeks", body)
        self.assertIn('id="event-search"', body)
        self.assertIn('id="event-source-filter"', body)
        self.assertIn('id="event-visibility-filter"', body)
        self.assertIn("Actions", body)
        self.assertIn('id="mark-unsent"', body)
        self.assertIn("Mark Unsent", body)

    def test_emails_script_includes_mark_unsent_ui_state_handling(self):
        response = self.client.get("/static/emails.js")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("markUnsentBtn", body)
        self.assertIn("state: 'unsent'", body)
        self.assertIn("els.markUnsentBtn.hidden = !isSendLocked;", body)
        self.assertIn("const isSendLocked = isSent || isSending;", body)
        self.assertIn("window.confirm", body)

    def test_hidden_events_are_excluded_from_preview_outputs(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "events": [
                    {
                        "id": "visible-event",
                        "source": "custom",
                        "kind": "event",
                        "title": "Visible Fundraiser",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-12",
                        "time_text": "All Day",
                        "location": "Campus Center",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                        "status": "active",
                    },
                    {
                        "id": "hidden-event",
                        "source": "custom",
                        "kind": "event",
                        "title": "Internal Planning Note",
                        "start_date": "2026-03-11",
                        "end_date": "2026-03-11",
                        "time_text": "2:00 PM",
                        "location": "Faculty Lounge",
                        "category": "Planning",
                        "audiences": ["middle-school", "upper-school"],
                        "status": "hidden",
                    },
                ],
            },
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/preview")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        middle_html = payload["outputs"]["middle-school"]["html"]
        upper_html = payload["outputs"]["upper-school"]["html"]

        self.assertIn("Visible Fundraiser", middle_html)
        self.assertIn("Visible Fundraiser", upper_html)
        self.assertNotIn("Internal Planning Note", middle_html)
        self.assertNotIn("Internal Planning Note", upper_html)
        self.assertEqual(payload["outputs"]["middle-school"]["source_event_count"], 1)
        self.assertEqual(payload["outputs"]["upper-school"]["source_event_count"], 1)


if __name__ == "__main__":
    unittest.main()