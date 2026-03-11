import unittest
from unittest.mock import patch

from sl_emails.poster.carousel import PosterEvent
from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app
from sl_emails.web.routes import poster_api


class AppApiTests(unittest.TestCase):
    def setUp(self):
        app = create_app({"TESTING": True, "EMAILS_STORE": MemoryWeeklyEmailStore()})
        self.client = app.test_client()

    def test_root_serves_signage_html(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Today's Events", response.get_data(as_text=True))

    def test_emails_route_serves_review_ui(self):
        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Weekly Email Review", body)
        self.assertIn("__EMAIL_REVIEW_DEFAULTS__", body)
        self.assertIn('id="event-search"', body)
        self.assertIn('id="event-source-filter"', body)
        self.assertIn('id="event-visibility-filter"', body)
        self.assertIn("Clear Filters", body)

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

    @patch.object(poster_api, "fetch_week_events")
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
                audiences=["upper-school"],
                team="Varsity Basketball",
                opponent="Opp",
                is_home=False,
                metadata={"source_type": "game", "sport": "basketball"},
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
        self.assertEqual(payload["events"][0]["audiences"], ["upper-school"])
        self.assertEqual(payload["events"][0]["team"], "Varsity Basketball")
        self.assertEqual(payload["events"][0]["opponent"], "Opp")
        self.assertFalse(payload["events"][0]["is_home"])
        self.assertEqual(payload["events"][0]["metadata"]["sport"], "basketball")

    def test_healthcheck(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})

    def test_weekly_email_backend_flow(self):
        save_response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "This Week at Kent Denver",
                "events": [
                    {
                        "id": "ms-basketball",
                        "kind": "game",
                        "source": "athletics",
                        "title": "Middle School Boys Basketball",
                        "team": "Middle School Boys Basketball",
                        "opponent": "Denver Academy",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-10",
                        "time": "4:00 PM",
                        "location": "Main Gym",
                        "category": "Basketball",
                        "audiences": ["middle-school"],
                        "is_home": True,
                    },
                    {
                        "id": "fundraiser",
                        "kind": "event",
                        "source": "custom",
                        "title": "Food Drive",
                        "start_date": "2026-03-11",
                        "end_date": "2026-03-13",
                        "time": "All Day",
                        "location": "Campus Center",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                    },
                ],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        save_payload = save_response.get_json()
        assert save_payload is not None
        self.assertEqual(save_payload["week"]["status"], "draft")
        self.assertEqual(len(save_payload["week"]["events"]), 2)

        preview_response = self.client.post("/api/emails/weeks/2026-03-09/preview")
        self.assertEqual(preview_response.status_code, 200)
        preview_payload = preview_response.get_json()
        assert preview_payload is not None
        self.assertIn("Food Drive", preview_payload["outputs"]["middle-school"]["html"])
        self.assertIn("Food Drive", preview_payload["outputs"]["upper-school"]["html"])
        self.assertIn("Middle School Boys Basketball", preview_payload["outputs"]["middle-school"]["html"])
        self.assertNotIn("Middle School Boys Basketball", preview_payload["outputs"]["upper-school"]["html"])

        blocked_response = self.client.get("/api/emails/weeks/2026-03-09/sender-output")
        self.assertEqual(blocked_response.status_code, 409)

        approve_response = self.client.post(
            "/api/emails/weeks/2026-03-09/approve",
            headers={"X-Email-Actor": "tester"},
        )
        self.assertEqual(approve_response.status_code, 200)
        approve_payload = approve_response.get_json()
        assert approve_payload is not None
        self.assertTrue(approve_payload["week"]["approval"]["approved"])
        self.assertEqual(approve_payload["week"]["approval"]["approved_by"], "tester")

        sender_response = self.client.get("/api/emails/weeks/2026-03-09/sender-output?audience=middle-school")
        self.assertEqual(sender_response.status_code, 200)
        sender_payload = sender_response.get_json()
        assert sender_payload is not None
        self.assertEqual(sender_payload["output"]["audience"], "middle-school")
        self.assertIn("Sports", sender_payload["output"]["subject"])
        self.assertIn("Food Drive", sender_payload["output"]["html"])
        self.assertFalse(sender_payload["sent"]["sent"])
        self.assertFalse(sender_payload["sent"]["sending"])

        claim_response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Email-Actor": "sender-bot"},
        )
        self.assertEqual(claim_response.status_code, 200)
        claim_payload = claim_response.get_json()
        assert claim_payload is not None
        self.assertTrue(claim_payload["sent"]["sending"])
        self.assertEqual(claim_payload["sent"]["sending_by"], "sender-bot")

        duplicate_claim = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Email-Actor": "sender-bot"},
        )
        self.assertEqual(duplicate_claim.status_code, 409)

        sender_during_claim = self.client.get("/api/emails/weeks/2026-03-09/sender-output?audience=upper-school")
        self.assertEqual(sender_during_claim.status_code, 200)
        sender_during_payload = sender_during_claim.get_json()
        assert sender_during_payload is not None
        self.assertTrue(sender_during_payload["sent"]["sending"])

        sent_response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sent"},
            headers={"X-Email-Actor": "sender-bot"},
        )
        self.assertEqual(sent_response.status_code, 200)
        sent_payload = sent_response.get_json()
        assert sent_payload is not None
        self.assertTrue(sent_payload["sent"]["sent"])
        self.assertEqual(sent_payload["sent"]["sent_by"], "sender-bot")
        self.assertFalse(sent_payload["sent"]["sending"])

        sender_after_sent = self.client.get("/api/emails/weeks/2026-03-09/sender-output?audience=upper-school")
        self.assertEqual(sender_after_sent.status_code, 200)
        sender_after_payload = sender_after_sent.get_json()
        assert sender_after_payload is not None
        self.assertTrue(sender_after_payload["sent"]["sent"])

    def test_weekly_save_infers_middle_school_audience_for_source_imports(self):
        save_response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "This Week at Kent Denver",
                "events": [
                    {
                        "id": "ms-soccer",
                        "kind": "game",
                        "source": "athletics",
                        "title": "Middle School Girls Soccer",
                        "team": "Middle School Girls Soccer",
                        "subtitle": "vs. Front Range",
                        "opponent": "Front Range",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-10",
                        "time_text": "4:00 PM",
                        "location": "North Field",
                        "category": "Soccer",
                        "is_home": True,
                        "metadata": {"source_type": "game"},
                    }
                ],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        save_payload = save_response.get_json()
        assert save_payload is not None
        event = save_payload["week"]["events"][0]
        self.assertEqual(event["audiences"], ["middle-school"])

        preview_response = self.client.post("/api/emails/weeks/2026-03-09/preview")

        self.assertEqual(preview_response.status_code, 200)
        preview_payload = preview_response.get_json()
        assert preview_payload is not None
        self.assertIn("Middle School Girls Soccer", preview_payload["outputs"]["middle-school"]["html"])
        self.assertNotIn("Middle School Girls Soccer", preview_payload["outputs"]["upper-school"]["html"])

    def test_claim_send_requires_approval(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/sent", json={"state": "sending"})

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("approved", payload["error"].lower())

    def test_mark_sent_requires_approval(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/sent")

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("approved", payload["error"].lower())

    def test_mark_unsent_clears_sent_state_and_preserves_approval(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sent"},
            headers={"X-Email-Actor": "sender-bot"},
        )

        response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "unsent"},
            headers={"X-Email-Actor": "admin-ui"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertFalse(payload["sent"]["sent"])
        self.assertFalse(payload["sent"]["sending"])
        self.assertEqual(payload["sent"]["sent_by"], "")
        self.assertEqual(payload["sent"]["sending_by"], "")
        self.assertTrue(payload["week"]["approval"]["approved"])

    def test_mark_unsent_clears_sending_lock_and_save_still_resets_approval(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Original Heading",
                "events": [],
            },
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Email-Actor": "sender-bot"},
        )

        reset_response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "unsent"},
            headers={"X-Email-Actor": "admin-ui"},
        )

        self.assertEqual(reset_response.status_code, 200)
        reset_payload = reset_response.get_json()
        assert reset_payload is not None
        self.assertFalse(reset_payload["sent"]["sent"])
        self.assertFalse(reset_payload["sent"]["sending"])
        self.assertTrue(reset_payload["week"]["approval"]["approved"])

        save_response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Updated Heading",
                "events": [],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        save_payload = save_response.get_json()
        assert save_payload is not None
        self.assertFalse(save_payload["week"]["approval"]["approved"])
        self.assertFalse(save_payload["week"]["sent"]["sent"])
        self.assertFalse(save_payload["week"]["sent"]["sending"])

    def test_create_custom_event_resets_approval(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve")

        event_response = self.client.post(
            "/api/emails/weeks/2026-03-09/events",
            json={
                "title": "Admissions Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "time": "6:00 PM",
                "location": "Welcome Center",
                "category": "Admissions",
            },
        )

        self.assertEqual(event_response.status_code, 201)
        payload = event_response.get_json()
        assert payload is not None
        self.assertFalse(payload["week"]["approval"]["approved"])
        self.assertEqual(payload["event"]["source"], "custom")


if __name__ == "__main__":
    unittest.main()