import unittest

from sl_emails.services.activity_log import MemoryActivityLogStore
from sl_emails.services.admin_settings import MemoryAdminSettingsStore
from sl_emails.services.request_store import MemoryEventRequestStore
from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app


class EmailsAdminUiTests(unittest.TestCase):
    def setUp(self):
        app = create_app(
            {
                "TESTING": True,
                "SESSION_COOKIE_SECURE": False,
                "EMAILS_STORE": MemoryWeeklyEmailStore(),
                "EMAILS_REQUEST_STORE": MemoryEventRequestStore(),
                "EMAILS_SETTINGS_STORE": MemoryAdminSettingsStore(),
                "EMAILS_ACTIVITY_STORE": MemoryActivityLogStore(),
            }
        )
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["auth_user"] = {"email": "appdev@kentdenver.org", "name": "App Dev"}

    def test_emails_page_exposes_dashboard_filters(self):
        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("System Status", body)
        self.assertIn('id="event-search"', body)
        self.assertIn('id="event-source-filter"', body)
        self.assertIn('id="event-visibility-filter"', body)
        self.assertIn("Actions", body)
        self.assertIn('id="send-now"', body)
        self.assertIn("Send Now", body)
        self.assertIn('id="mark-unsent"', body)
        self.assertIn("Mark Unsent", body)
        self.assertIn("Refresh Events", body)
        self.assertIn("Settings", body)
        self.assertIn('id="week-picker-rail"', body)
        self.assertIn('id="generate-ai"', body)
        self.assertIn('id="clear-week"', body)
        self.assertIn('id="week-subject-ms"', body)
        self.assertIn('id="week-subject-us"', body)
        self.assertIn("Submission Queue", body)
        self.assertIn('id="request-summary"', body)
        self.assertIn('id="request-list"', body)
        self.assertIn("Recent Activity", body)
        self.assertIn('id="activity-list"', body)
        self.assertIn('"iconOptions"', body)

    def test_emails_script_includes_mark_unsent_ui_state_handling(self):
        response = self.client.get("/static/emails.js")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("markUnsentBtn", body)
        self.assertIn("sendNowBtn", body)
        self.assertIn("/manual-send", body)
        self.assertIn("els.sendNowBtn.disabled = !state.week || state.dirty || isSendLocked || isSkipped;", body)
        self.assertIn('els.sendNowBtn.textContent = !state.week || isApproved ? "Send Now" : "Approve & Send";', body)
        self.assertIn("Approve it and send both audience emails now?", body)
        self.assertIn('state: "unsent"', body)
        self.assertIn("els.markUnsentBtn.hidden = !isSendLocked;", body)
        self.assertIn("els.createBtn.disabled = !state.week || isSendLocked;", body)
        self.assertIn("const isSendLocked = isSent || isSending;", body)
        self.assertIn("/source-refresh", body)
        self.assertIn("window.confirm", body)
        self.assertIn("status-review-email", body)
        self.assertIn("status-delivery", body)
        self.assertIn("fetchWeekActivity", body)
        self.assertIn("activityList", body)
        self.assertIn("/weeks/${weekId}/requests", body)
        self.assertIn("/weeks/${weekId}/activity", body)
        self.assertIn("reviewRequest", body)
        self.assertIn("requestList", body)
        self.assertIn("generateAiCopy", body)
        self.assertIn("clearWeek", body)
        self.assertIn("deliveryOptions", body)

    def test_settings_page_exposes_automation_delivery_fields(self):
        response = self.client.get("/emails/settings")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Automation Delivery", body)
        self.assertIn('id="email-from-name"', body)
        self.assertIn('id="reply-to-email"', body)
        self.assertIn('id="sender-timezone"', body)
        self.assertIn('id="middle-school-to"', body)
        self.assertIn('id="middle-school-bcc"', body)
        self.assertIn('id="upper-school-to"', body)
        self.assertIn('id="upper-school-bcc"', body)
        self.assertIn("Apps Script Manual Send", body)
        self.assertIn('id="apps-script-web-app-url"', body)
        self.assertIn('id="automation-key"', body)
        self.assertIn('id="reveal-automation-key"', body)
        self.assertIn('id="copy-automation-key"', body)
        self.assertIn('id="rotate-automation-key"', body)
        self.assertIn('id="test-apps-script"', body)
        self.assertIn("Test Connection", body)
        self.assertIn('id="save-settings"', body)
        self.assertIn("Save All Settings", body)

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
