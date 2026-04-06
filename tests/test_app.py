import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from sl_emails.services import signage_ingest
from sl_emails.services.activity_log import MemoryActivityLogStore
from sl_emails.services.admin_settings import MemoryAdminSettingsStore
from sl_emails.services.event_shapes import PosterEvent, SourceFetchStatus, WeekEventsFetchResult
from sl_emails.services.request_store import MemoryEventRequestStore
from sl_emails.services.signage_store import MemorySignageStore
from sl_emails.services import weekly_ingest
from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app
from sl_emails.web.request_protection import PublicRequestProtector
from sl_emails.web import support as web_support


class _FailingReviewRequestStore(MemoryEventRequestStore):
    def review_request(self, *args, **kwargs):
        raise RuntimeError("review storage unavailable")


class _FailingActivityLogStore(MemoryActivityLogStore):
    def log(self, *args, **kwargs):
        raise RuntimeError("activity storage unavailable")


class _MetadataFailingWeeklyStore(MemoryWeeklyEmailStore):
    def update_week_metadata(self, week_id, metadata):
        raise RuntimeError("week metadata unavailable")


class AppApiTests(unittest.TestCase):
    def setUp(self):
        signage_store = MemorySignageStore()
        signage_store.save_day(
            "2026-03-23",
            {
                "events": [
                    {
                        "title": "Varsity Soccer",
                        "subtitle": "vs. Front Range",
                        "date": "2026-03-23",
                        "time": "4:00 PM",
                        "location": "Main Field",
                        "category": "Soccer",
                        "source": "athletics",
                        "badge": "HOME",
                        "priority": 4,
                        "accent": "#0066ff",
                        "audiences": ["upper-school"],
                        "team": "Varsity Soccer",
                        "opponent": "Front Range",
                        "is_home": True,
                        "metadata": {"source_type": "game", "sport": "soccer"},
                    }
                ],
                "source_summary": {"athletics_events": 1, "arts_events": 0, "total_events": 1},
                "metadata": {},
            },
        )
        signage_store.save_day(
            "2026-04-02",
            {
                "events": [
                    {
                        "title": "Spring Play",
                        "subtitle": "Theater",
                        "date": "2026-04-02",
                        "time": "7:00 PM",
                        "location": "Richards Hall",
                        "category": "Theater",
                        "source": "arts",
                        "badge": "EVENT",
                        "priority": 4,
                        "accent": "#A11919",
                        "audiences": ["upper-school"],
                        "team": "Spring Play",
                        "opponent": "",
                        "is_home": True,
                        "metadata": {"source_type": "arts"},
                    }
                ],
                "source_summary": {"athletics_events": 0, "arts_events": 1, "total_events": 1},
                "metadata": {},
            },
        )
        app = create_app(
            {
                "TESTING": True,
                "SESSION_COOKIE_SECURE": False,
                "SIGNAGE_STORE": signage_store,
                "EMAILS_STORE": MemoryWeeklyEmailStore(),
                "EMAILS_REQUEST_STORE": MemoryEventRequestStore(),
                "EMAILS_SETTINGS_STORE": MemoryAdminSettingsStore(),
                "EMAILS_ACTIVITY_STORE": MemoryActivityLogStore(),
            }
        )
        self.client = app.test_client()
        self.login_as()

    def login_as(self, email: str = "appdev@kentdenver.org", name: str = "App Dev") -> None:
        with self.client.session_transaction() as session:
            session["auth_user"] = {"email": email, "name": name}

    def logout(self) -> None:
        with self.client.session_transaction() as session:
            session.clear()

    @patch.object(web_support, "today_in_timezone")
    @patch.object(web_support, "_seconds_until_next_signage_midnight")
    def test_signage_route_serves_firestore_snapshot(self, mock_ttl, mock_today):
        mock_ttl.return_value = 43200
        mock_today.return_value = weekly_ingest.iso_to_date("2026-03-23")
        response = self.client.get("/signage")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Today's Events", response.get_data(as_text=True))
        self.assertIn("Varsity Soccer", response.get_data(as_text=True))
        self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=43200, s-maxage=43200")

    def test_signage_route_accepts_testing_date_override(self):
        response = self.client.get("/signage?date=2026-04-02")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Thursday, April 02, 2026", response.get_data(as_text=True))
        self.assertIn("Spring Play", response.get_data(as_text=True))
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")

    def test_signage_route_rejects_invalid_testing_date_override(self):
        response = self.client.get("/signage?date=2026-04-31")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_data(as_text=True), "Invalid signage preview date. Use YYYY-MM-DD.")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")

    @patch.object(web_support, "today_in_timezone")
    def test_signage_route_does_not_cache_missing_snapshot(self, mock_today):
        mock_today.return_value = weekly_ingest.iso_to_date("2026-04-03")
        response = self.client.get("/signage")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Signage snapshot not found.")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")

    @patch.object(web_support, "today_in_timezone")
    @patch.object(web_support, "_signage_now")
    def test_signage_route_serves_previous_day_during_rollover_grace_window(self, mock_now, mock_today):
        mock_today.return_value = weekly_ingest.iso_to_date("2026-04-03")
        mock_now.return_value = datetime(2026, 4, 3, 0, 15, tzinfo=ZoneInfo("America/Denver"))
        response = self.client.get("/signage")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Today's Events", response.get_data(as_text=True))
        self.assertIn("Spring Play", response.get_data(as_text=True))
        self.assertIn("Thursday, April 02, 2026", response.get_data(as_text=True))
        self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=300, s-maxage=300")

    @patch.object(web_support, "today_in_timezone")
    @patch.object(web_support, "_signage_now")
    def test_signage_route_does_not_serve_previous_day_after_rollover_grace_window(self, mock_now, mock_today):
        mock_today.return_value = weekly_ingest.iso_to_date("2026-04-03")
        mock_now.return_value = datetime(2026, 4, 3, 6, 0, tzinfo=ZoneInfo("America/Denver"))
        response = self.client.get("/signage")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Signage snapshot not found.")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")

    @patch.object(web_support, "today_in_timezone")
    @patch.object(web_support, "_signage_now")
    def test_signage_route_returns_503_when_rollover_fallback_lookup_fails(self, mock_now, mock_today):
        mock_today.return_value = weekly_ingest.iso_to_date("2026-04-03")
        mock_now.return_value = datetime(2026, 4, 3, 0, 15, tzinfo=ZoneInfo("America/Denver"))
        signage_store = self.client.application.config["SIGNAGE_STORE"]
        with patch.object(signage_store, "get_day", side_effect=[None, RuntimeError("signage unavailable")]):
            response = self.client.get("/signage")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_data(as_text=True), "signage unavailable")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")

    def test_root_returns_plain_text_ok(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.get_data(as_text=True), "OK")

    @patch.object(signage_ingest, "fetch_signage_events")
    def test_signage_refresh_endpoint_creates_and_refreshes_day_snapshot(self, mock_fetch_signage_events):
        mock_fetch_signage_events.return_value = [
            PosterEvent(
                title="Spring Concert",
                subtitle="Music",
                date="2026-03-24",
                time="7:00 PM",
                location="PAC",
                category="Music",
                source="arts",
                badge="EVENT",
                priority=4,
                accent="#A11919",
                audiences=["upper-school"],
                team="Spring Concert",
                metadata={"source_type": "arts"},
            )
        ]

        self.client.application.config["EMAILS_AUTOMATION_KEY"] = ""
        forbidden = self.client.post("/api/signage/automation/days/2026-03-24/refresh")
        self.assertEqual(forbidden.status_code, 503)

        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"

        invalid = self.client.post(
            "/api/signage/automation/days/2026-03-24/refresh",
            headers={"X-Automation-Key": "wrong-key"},
        )
        self.assertEqual(invalid.status_code, 403)

        created = self.client.post(
            "/api/signage/automation/days/2026-03-24/refresh",
            headers={"X-Automation-Key": "secret-key", "X-Email-Actor": "google-apps-script"},
        )
        self.assertEqual(created.status_code, 200)
        created_payload = created.get_json()
        assert created_payload is not None
        self.assertEqual(created_payload["action"], "created")
        self.assertEqual(created_payload["reason"], "created_from_sources")
        self.assertEqual(created_payload["source_summary"]["arts_events"], 1)
        self.assertEqual(created_payload["day"]["metadata"]["ingest"]["actor"], "google-apps-script")
        self.assertEqual(created_payload["day"]["metadata"]["ingest"]["action"], "created")

        refreshed = self.client.post(
            "/api/signage/automation/days/2026-03-24/refresh",
            headers={"X-Automation-Key": "secret-key", "X-Email-Actor": "google-apps-script"},
        )
        self.assertEqual(refreshed.status_code, 200)
        refreshed_payload = refreshed.get_json()
        assert refreshed_payload is not None
        self.assertEqual(refreshed_payload["action"], "refreshed")
        self.assertEqual(refreshed_payload["reason"], "replaced_existing_snapshot")
        self.assertEqual(refreshed_payload["day"]["metadata"]["ingest"]["action"], "refreshed")

    @patch.object(signage_ingest, "fetch_signage_events")
    def test_local_signage_refresh_endpoint_creates_snapshot_in_testing(self, mock_fetch_signage_events):
        mock_fetch_signage_events.return_value = [
            PosterEvent(
                title="April Preview Game",
                subtitle="vs. Valor",
                date="2026-04-02",
                time="4:30 PM",
                location="Main Field",
                category="Soccer",
                source="athletics",
                badge="HOME",
                priority=4,
                accent="#0066ff",
                audiences=["upper-school"],
                team="April Preview Game",
                opponent="Valor",
                is_home=True,
                metadata={"source_type": "game", "sport": "soccer"},
            )
        ]

        response = self.client.post("/api/signage/local/days/2026-04-02/refresh")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["action"], "refreshed")
        self.assertEqual(payload["day_id"], "2026-04-02")
        self.assertEqual(payload["day"]["metadata"]["ingest"]["actor"], "local-dev")
        self.assertEqual(payload["day"]["events"][0]["title"], "April Preview Game")

    def test_emails_route_requires_login_when_unauthenticated(self):
        self.logout()
        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=/emails", response.headers["Location"])

    def test_login_route_serves_sign_in_ui(self):
        self.logout()
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Admin Sign-In", response.get_data(as_text=True))
        self.assertEqual(self.client.application.config["SESSION_COOKIE_NAME"], "__session")

    def test_create_app_requires_runtime_configuration_outside_testing(self):
        with self.assertRaises(RuntimeError):
            create_app(
                {
                    "SECRET_KEY": "",
                    "EMAILS_AUTOMATION_KEY": "",
                    "GOOGLE_OAUTH_CLIENT_ID": "",
                    "GOOGLE_OAUTH_CLIENT_SECRET": "",
                    "GOOGLE_OAUTH_CALLBACK_URL": "",
                }
            )

    def test_create_app_local_dev_allows_http_callback_defaults(self):
        app = create_app(
            {
                "EMAILS_LOCAL_DEV": "1",
                "SECRET_KEY": "local-dev-secret",
                "EMAILS_AUTOMATION_KEY": "local-dev-automation-key",
                "GOOGLE_OAUTH_CLIENT_ID": "client-id",
                "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
            }
        )

        self.assertFalse(app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(app.config["PREFERRED_URL_SCHEME"], "http")

    def test_emails_route_serves_review_ui(self):
        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Weekly Email Review", body)
        self.assertIn("__EMAIL_REVIEW_DEFAULTS__", body)
        self.assertIn('id="event-search"', body)
        self.assertIn('id="event-source-filter"', body)
        self.assertIn('id="event-visibility-filter"', body)
        self.assertIn("System Status", body)

    def test_emails_route_honors_week_query_parameter(self):
        self.logout()
        response = self.client.get("/emails?week=2026-03-09")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=/emails?week=2026-03-09", response.headers["Location"])

        self.login_as()
        response = self.client.get("/emails?week=2026-03-09")

        self.assertEqual(response.status_code, 200)
        self.assertIn('"weekId": "2026-03-09"', response.get_data(as_text=True))

    def test_emails_route_normalizes_non_monday_week_query_parameter(self):
        response = self.client.get("/emails?week=2026-03-11")

        self.assertEqual(response.status_code, 200)
        self.assertIn('"weekId": "2026-03-09"', response.get_data(as_text=True))

    def test_public_request_page_is_available_without_login(self):
        self.logout()

        response = self.client.get("/request")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Request an event for the weekly sports emails.", body)
        self.assertIn('id="request-form"', body)
        self.assertIn("Food Drive", body)
        self.assertIn('name="sport_category"', body)

    def test_public_request_submission_routes_to_review_week(self):
        self.logout()

        response = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Robotics Night",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "time_text": "6:00 PM",
                "location": "Innovation Lab",
                "category": "STEM",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["request"]["status"], "pending")
        self.assertEqual(payload["request"]["week_id"], "2026-03-09")
        self.assertIn("March 9", payload["week_label"])
        self.assertIn("2026", payload["week_label"])
        self.assertTrue(payload["request"]["metadata"]["submission"]["ip_hash"])
        self.assertTrue(payload["request"]["metadata"]["submission"]["user_agent_hash"])

    def test_public_request_submission_blocks_honeypot_payloads(self):
        self.logout()

        response = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Robotics Night",
                "start_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
                "website": "https://spam.example.test",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_public_request_submission_rate_limits_repeat_attempts(self):
        self.logout()
        self.client.application.config["EMAILS_REQUEST_PROTECTOR"] = PublicRequestProtector(max_attempts=1, window_seconds=3600)

        first = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Robotics Night",
                "start_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            },
        )
        second = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Second Robotics Night",
                "start_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            },
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    def test_non_allowlisted_user_is_redirected_to_access_denied(self):
        self.logout()
        self.login_as(email="outsider@kentdenver.org", name="Outside User")

        response = self.client.get("/emails")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/access-denied")

    def test_healthcheck(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})

    def test_activity_log_failures_do_not_break_successful_mutations(self):
        self.client.application.config["EMAILS_ACTIVITY_STORE"] = _FailingActivityLogStore()

        response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "events": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["week"]["week_id"], "2026-03-09")

    def test_activity_api_returns_recent_week_activity(self):
        activity_store = self.client.application.config["EMAILS_ACTIVITY_STORE"]
        activity_store.log(
            event_type="scheduled_ingest",
            status="success",
            actor="google-apps-script",
            week_id="2026-03-09",
            message="Created draft",
            details={"reason": "created_from_sources"},
        )
        activity_store.log(
            event_type="send",
            status="success",
            actor="google-apps-script",
            week_id="2026-03-09",
            message="Marked sent",
            details={"state": "sent"},
        )

        response = self.client.get("/api/emails/weeks/2026-03-09/activity?limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(len(payload["activity"]), 2)
        self.assertEqual({item["event_type"] for item in payload["activity"]}, {"scheduled_ingest", "send"})

    def test_admin_api_requires_authentication(self):
        self.logout()

        response = self.client.get("/api/emails/weeks/2026-03-09")

        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["error"], "Authentication required")
        self.assertIn("/login", payload["login_url"])

    def test_settings_bootstrap_and_update(self):
        response = self.client.get("/api/emails/settings")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(
            payload["settings"]["allowed_admin_emails"],
            ["appdev@kentdenver.org", "studentleader@kentdenver.org"],
        )

        update_response = self.client.put(
            "/api/emails/settings",
            json={
                "allowed_admin_emails": [
                    "appdev@kentdenver.org",
                    "studentleader@kentdenver.org",
                    "newadmin@kentdenver.org",
                ],
                "ops_notification_emails": [
                    "appdev@kentdenver.org",
                    "ops@kentdenver.org",
                ],
            },
        )

        self.assertEqual(update_response.status_code, 200)
        update_payload = update_response.get_json()
        assert update_payload is not None
        self.assertIn("newadmin@kentdenver.org", update_payload["settings"]["allowed_admin_emails"])
        self.assertEqual(
            update_payload["settings"]["ops_notification_emails"],
            ["appdev@kentdenver.org", "ops@kentdenver.org"],
        )

    def test_settings_update_cannot_remove_current_user(self):
        response = self.client.put(
            "/api/emails/settings",
            json={
                "allowed_admin_emails": ["studentleader@kentdenver.org"],
                "ops_notification_emails": ["studentleader@kentdenver.org"],
            },
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("cannot remove your own email", payload["error"].lower())

    def test_scheduled_ingest_does_not_create_week_when_source_fetch_fails(self):
        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        failed_fetch = WeekEventsFetchResult(
            events=[],
            source_statuses=[
                SourceFetchStatus(source="athletics", ok=False, event_count=0, error="athletics source unavailable", fetched_at="2026-03-08T15:00:00Z"),
                SourceFetchStatus(source="arts", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
            ],
        )

        with patch.object(weekly_ingest, "fetch_week_events", return_value=failed_fetch):
            response = self.client.post(
                "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
                headers={"X-Automation-Key": "secret-key"},
            )

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("source_health", payload)
        self.assertIsNone(self.client.application.config["EMAILS_STORE"].get_week("2026-03-09"))

    def test_zero_event_ingest_succeeds_when_sources_are_healthy(self):
        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        empty_fetch = WeekEventsFetchResult(
            events=[],
            source_statuses=[
                SourceFetchStatus(source="athletics", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
                SourceFetchStatus(source="arts", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
            ],
        )

        with patch.object(weekly_ingest, "fetch_week_events", return_value=empty_fetch):
            response = self.client.post(
                "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
                headers={"X-Automation-Key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["source_summary"]["total_events"], 0)
        self.assertEqual(len(payload["source_health"]), 2)
        self.assertEqual(len(payload["week"]["events"]), 0)

    def test_source_refresh_failure_does_not_overwrite_existing_week(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "events": [
                    {
                        "id": "existing-event",
                        "source": "custom",
                        "kind": "event",
                        "title": "Keep Me",
                        "start_date": "2026-03-11",
                        "end_date": "2026-03-11",
                        "time_text": "All Day",
                        "location": "Campus",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                    }
                ],
            },
        )

        failed_fetch = WeekEventsFetchResult(
            events=[],
            source_statuses=[
                SourceFetchStatus(source="athletics", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
                SourceFetchStatus(source="arts", ok=False, event_count=0, error="arts calendar timeout", fetched_at="2026-03-08T15:00:00Z"),
            ],
        )

        with patch.object(weekly_ingest, "fetch_week_events", return_value=failed_fetch):
            response = self.client.post("/api/emails/weeks/2026-03-09/source-refresh")

        self.assertEqual(response.status_code, 503)
        week = self.client.application.config["EMAILS_STORE"].get_week("2026-03-09")
        assert week is not None
        self.assertEqual([event.title for event in week.events], ["Keep Me"])
        self.assertEqual(week.metadata["manual_refresh"]["status"], "failed")

    def test_signage_refresh_failure_does_not_blank_existing_day(self):
        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        failed_fetch = WeekEventsFetchResult(
            events=[],
            source_statuses=[
                SourceFetchStatus(source="athletics", ok=False, event_count=0, error="athletics source unavailable", fetched_at="2026-03-24T06:00:00Z"),
                SourceFetchStatus(source="arts", ok=True, event_count=1, error="", fetched_at="2026-03-24T06:00:00Z"),
            ],
        )

        with patch.object(signage_ingest, "fetch_signage_events", return_value=failed_fetch):
            response = self.client.post(
                "/api/signage/automation/days/2026-03-23/refresh",
                headers={"X-Automation-Key": "secret-key", "X-Email-Actor": "google-apps-script"},
            )

        self.assertEqual(response.status_code, 503)
        day = self.client.application.config["SIGNAGE_STORE"].get_day("2026-03-23")
        assert day is not None
        self.assertEqual(day.events[0].title, "Varsity Soccer")
        self.assertEqual(day.metadata["ingest"]["status"], "failed")

    def test_metadata_update_failures_do_not_break_successful_ingest(self):
        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        self.client.application.config["EMAILS_STORE"] = _MetadataFailingWeeklyStore()
        success_fetch = WeekEventsFetchResult(
            events=[],
            source_statuses=[
                SourceFetchStatus(source="athletics", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
                SourceFetchStatus(source="arts", ok=True, event_count=0, error="", fetched_at="2026-03-08T15:00:00Z"),
            ],
        )

        with patch.object(weekly_ingest, "fetch_week_events", return_value=success_fetch):
            response = self.client.post(
                "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
                headers={"X-Automation-Key": "secret-key"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["action"], "created")

    @patch.object(weekly_ingest, "fetch_week_events")
    def test_scheduled_ingest_creates_week_then_skips_existing_draft(self, mock_fetch_week_events):
        mock_fetch_week_events.return_value = [
            PosterEvent(
                title="Varsity Basketball",
                subtitle="vs. Front Range",
                date="2026-03-10",
                time="4:00 PM",
                location="Main Gym",
                category="Basketball",
                source="athletics",
                badge="HOME",
                priority=3,
                accent="#0C3A6B",
                audiences=["upper-school"],
                team="Varsity Basketball",
                opponent="Front Range",
                is_home=True,
                metadata={"source_type": "game", "sport": "basketball"},
            ),
            PosterEvent(
                title="Spring Concert",
                subtitle="Music",
                date="2026-03-11",
                time="7:00 PM",
                location="PAC",
                category="Music",
                source="arts",
                badge="EVENT",
                priority=4,
                accent="#A11919",
                audiences=["upper-school"],
                team="Spring Concert",
                metadata={"source_type": "arts"},
            ),
        ]

        self.client.application.config["EMAILS_AUTOMATION_KEY"] = ""
        forbidden = self.client.post("/api/emails/automation/weeks/2026-03-09/scheduled-ingest")
        self.assertEqual(forbidden.status_code, 503)

        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        created = self.client.post(
            "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
            headers={"X-Automation-Key": "wrong-key"},
        )
        self.assertEqual(created.status_code, 403)

        created = self.client.post(
            "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
            headers={"X-Automation-Key": "secret-key"},
        )

        self.assertEqual(created.status_code, 200)
        created_payload = created.get_json()
        assert created_payload is not None
        self.assertEqual(created_payload["action"], "created")
        self.assertEqual(created_payload["reason"], "created_from_sources")
        self.assertEqual(created_payload["source_summary"]["athletics_events"], 1)
        self.assertEqual(created_payload["source_summary"]["arts_events"], 1)
        self.assertEqual(len(created_payload["week"]["events"]), 2)
        self.assertEqual(created_payload["week"]["metadata"]["scheduled_ingest"]["action"], "created")
        self.assertEqual(mock_fetch_week_events.call_count, 1)

        skipped = self.client.post(
            "/api/emails/automation/weeks/2026-03-09/scheduled-ingest",
            headers={"X-Automation-Key": "secret-key"},
        )

        self.assertEqual(skipped.status_code, 200)
        skipped_payload = skipped.get_json()
        assert skipped_payload is not None
        self.assertEqual(skipped_payload["action"], "skipped")
        self.assertEqual(skipped_payload["reason"], "existing_draft")
        self.assertEqual(skipped_payload["week"]["metadata"]["scheduled_ingest"]["action"], "skipped")
        self.assertEqual(mock_fetch_week_events.call_count, 1)

    @patch.object(weekly_ingest, "fetch_week_events")
    def test_source_refresh_preserves_custom_events_and_resets_review_state(self, mock_fetch_week_events):
        mock_fetch_week_events.return_value = [
            PosterEvent(
                title="Updated Varsity Basketball",
                subtitle="vs. Kent",
                date="2026-03-10",
                time="5:00 PM",
                location="Main Gym",
                category="Basketball",
                source="athletics",
                badge="AWAY",
                priority=3,
                accent="#0C3A6B",
                audiences=["upper-school"],
                team="Updated Varsity Basketball",
                opponent="Kent",
                is_home=False,
                metadata={"source_type": "game", "sport": "basketball"},
            )
        ]

        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Original Heading",
                "notes": "Keep these notes",
                "delivery": {"mode": "postpone", "send_on": "2026-03-11"},
                "copy_overrides": {
                    "hero_text": "Hero summary",
                    "cta_text": "Come support the teams.",
                },
                "subject_overrides": {
                    "middle-school": "Middle School Athletics Update",
                    "upper-school": "Upper School Athletics Update",
                },
                "events": [
                    {
                        "id": "legacy-athletics",
                        "kind": "game",
                        "source": "athletics",
                        "title": "Old Athletics Row",
                        "team": "Old Athletics Row",
                        "opponent": "Legacy Opponent",
                        "start_date": "2026-03-10",
                        "end_date": "2026-03-10",
                        "time_text": "4:00 PM",
                        "location": "Old Gym",
                        "category": "Basketball",
                        "audiences": ["upper-school"],
                    },
                    {
                        "id": "custom-row",
                        "kind": "event",
                        "source": "custom",
                        "title": "Custom Announcement",
                        "start_date": "2026-03-12",
                        "end_date": "2026-03-12",
                        "time_text": "All Day",
                        "location": "Campus",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                        "status": "hidden",
                    },
                ],
            },
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Email-Actor": "sender-bot"},
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/source-refresh")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["action"], "refreshed")
        self.assertEqual(payload["reason"], "replaced_source_events_preserved_custom")
        self.assertEqual(payload["week"]["heading"], "Original Heading")
        self.assertEqual(payload["week"]["notes"], "Keep these notes")
        self.assertEqual(payload["week"]["delivery"]["mode"], "postpone")
        self.assertEqual(payload["week"]["delivery"]["send_on"], "2026-03-11")
        self.assertEqual(payload["week"]["copy_overrides"]["hero_text"], "Hero summary")
        self.assertEqual(payload["week"]["copy_overrides"]["cta_text"], "Come support the teams.")
        self.assertEqual(payload["week"]["subject_overrides"]["middle-school"], "Middle School Athletics Update")
        self.assertEqual(payload["week"]["subject_overrides"]["upper-school"], "Upper School Athletics Update")
        self.assertFalse(payload["week"]["approval"]["approved"])
        self.assertFalse(payload["week"]["sent"]["sent"])
        self.assertFalse(payload["week"]["sent"]["sending"])
        self.assertEqual(payload["week"]["metadata"]["manual_refresh"]["status"], "success")
        titles = [event["title"] for event in payload["week"]["events"]]
        self.assertIn("Custom Announcement", titles)
        self.assertIn("Updated Varsity Basketball", titles)
        self.assertNotIn("Old Athletics Row", titles)

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
        self.assertEqual(blocked_response.status_code, 200)
        blocked_payload = blocked_response.get_json()
        assert blocked_payload is not None
        self.assertFalse(blocked_payload["approved"])
        self.assertEqual(blocked_payload["delivery"]["mode"], "default")
        self.assertEqual(blocked_payload["outputs"], {})

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

    def test_preview_and_sender_output_include_subject_overrides_notes_links_and_icons(self):
        save_response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Championship Week",
                "notes": "Families can use the links below for details and campus logistics.",
                "subject_overrides": {
                    "middle-school": "Middle School Weekly Highlights",
                    "upper-school": "Upper School Weekly Highlights",
                },
                "events": [
                    {
                        "id": "community-night",
                        "kind": "event",
                        "source": "custom",
                        "title": "Community Night",
                        "start_date": "2026-03-11",
                        "end_date": "2026-03-11",
                        "time_text": "6:30 PM",
                        "location": "Campus Center",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                        "description": "Bring a canned good for the service drive.",
                        "link": "https://www.kentdenver.org/community-night",
                        "icon": "calendar-days",
                    }
                ],
            },
        )

        self.assertEqual(save_response.status_code, 200)

        preview_response = self.client.post("/api/emails/weeks/2026-03-09/preview")

        self.assertEqual(preview_response.status_code, 200)
        preview_payload = preview_response.get_json()
        assert preview_payload is not None
        middle_output = preview_payload["outputs"]["middle-school"]
        self.assertEqual(middle_output["subject"], "Middle School Weekly Highlights")
        self.assertEqual(middle_output["default_subject"], "Sports and Performances This Week: March 9 - 15")
        self.assertIn("Championship Week", middle_output["html"])
        self.assertIn("Families can use the links below for details and campus logistics.", middle_output["html"])
        self.assertIn("Bring a canned good for the service drive.", middle_output["html"])
        self.assertIn("https://www.kentdenver.org/community-night", middle_output["html"])
        self.assertIn("/static/icons/calendar.svg", middle_output["html"])

        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "tester"})
        sender_response = self.client.get("/api/emails/weeks/2026-03-09/sender-output?audience=upper-school")

        self.assertEqual(sender_response.status_code, 200)
        sender_payload = sender_response.get_json()
        assert sender_payload is not None
        self.assertEqual(sender_payload["output"]["subject"], "Upper School Weekly Highlights")
        self.assertIn("/static/icons/calendar.svg", sender_payload["output"]["html"])

    def test_save_week_normalizes_non_monday_request_to_week_monday(self):
        response = self.client.put(
            "/api/emails/weeks/2026-03-11",
            json={
                "start_date": "2026-03-11",
                "end_date": "2026-03-15",
                "events": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["week"]["week_id"], "2026-03-09")
        self.assertEqual(payload["week"]["start_date"], "2026-03-09")

    def test_skip_delivery_blocks_approval_and_sender_output_reflects_skip(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "delivery": {"mode": "skip"},
                "events": [],
            },
        )

        approve = self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.assertEqual(approve.status_code, 409)
        approve_payload = approve.get_json()
        assert approve_payload is not None
        self.assertIn("no email this week", approve_payload["error"].lower())

        sender_output = self.client.get("/api/emails/weeks/2026-03-09/sender-output")
        self.assertEqual(sender_output.status_code, 200)
        sender_payload = sender_output.get_json()
        assert sender_payload is not None
        self.assertFalse(sender_payload["approved"])
        self.assertEqual(sender_payload["delivery"]["mode"], "skip")

    def test_clear_week_resets_events_copy_subjects_and_delivery(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Loaded Week",
                "notes": "Clear me",
                "subject_overrides": {"middle-school": "Keep?", "upper-school": "Nope"},
                "delivery": {"mode": "postpone", "send_on": "2026-03-11"},
                "copy_overrides": {"hero_text": "Generated copy", "cta_text": "Bring someone"},
                "events": [
                    {
                        "id": "custom-row",
                        "source": "custom",
                        "kind": "event",
                        "title": "Custom Row",
                        "start_date": "2026-03-11",
                        "end_date": "2026-03-11",
                        "time_text": "All Day",
                        "location": "Campus",
                        "category": "Community",
                        "audiences": ["middle-school", "upper-school"],
                    }
                ],
            },
        )

        clear = self.client.post("/api/emails/weeks/2026-03-09/clear", headers={"X-Email-Actor": "admin-ui"})
        self.assertEqual(clear.status_code, 200)
        payload = clear.get_json()
        assert payload is not None
        self.assertEqual(payload["week"]["heading"], "This Week at Kent Denver")
        self.assertEqual(payload["week"]["notes"], "")
        self.assertEqual(payload["week"]["subject_overrides"], {})
        self.assertEqual(payload["week"]["copy_overrides"]["hero_text"], "")
        self.assertEqual(payload["week"]["copy_overrides"]["cta_text"], "")
        self.assertEqual(payload["week"]["delivery"]["mode"], "default")
        self.assertEqual(payload["week"]["delivery"]["send_on"], "2026-03-08")
        self.assertEqual(payload["week"]["events"], [])

    @patch("sl_emails.web.routes.emails_api.generate_week_copy")
    def test_ai_copy_endpoint_updates_editable_copy_fields(self, mock_generate_week_copy):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        mock_generate_week_copy.return_value = {
            "heading": "AI Week",
            "notes": "AI note",
            "subject_overrides": {"middle-school": "AI MS", "upper-school": "AI US"},
            "copy_overrides": {
                "hero_text": "Hero",
                "intro_title": "Intro",
                "intro_text": "Summary",
                "spotlight_label": "Spotlight",
                "schedule_label": "Schedule",
                "also_on_schedule_label": "Also on schedule",
                "empty_day_template": "Nothing on {weekday}.",
                "cta_eyebrow": "Join Us",
                "cta_title": "See You There",
                "cta_text": "Bring a friend.",
            },
        }

        response = self.client.post("/api/emails/weeks/2026-03-09/ai-copy", headers={"X-Email-Actor": "admin-ui"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["week"]["heading"], "AI Week")
        self.assertEqual(payload["week"]["notes"], "AI note")
        self.assertEqual(payload["week"]["subject_overrides"]["middle-school"], "AI MS")
        self.assertEqual(payload["week"]["copy_overrides"]["hero_text"], "Hero")
        self.assertEqual(payload["week"]["copy_overrides"]["cta_text"], "Bring a friend.")

    def test_ai_copy_endpoint_returns_503_when_gemini_is_unconfigured(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/ai-copy", headers={"X-Email-Actor": "admin-ui"})

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("gemini api key", payload["error"].lower())

    def test_preview_uses_copy_override_text_when_present(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "copy_overrides": {
                    "hero_text": "Custom hero line",
                    "intro_title": "Custom intro",
                    "intro_text": "Personalized weekly summary.",
                    "cta_eyebrow": "Show Up",
                    "cta_title": "Make Some Noise",
                    "cta_text": "Bring the blue and white.",
                },
                "events": [],
            },
        )

        response = self.client.post("/api/emails/weeks/2026-03-09/preview")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        html = payload["outputs"]["middle-school"]["html"]
        self.assertIn("Custom hero line", html)
        self.assertIn("Custom intro", html)
        self.assertIn("Personalized weekly summary.", html)
        self.assertIn("Show Up", html)
        self.assertIn("Make Some Noise", html)
        self.assertIn("Bring the blue and white.", html)

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

    def test_mark_sent_requires_send_claim(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})

        response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sent"},
            headers={"X-Email-Actor": "sender-bot"},
        )

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("claimed for sending", payload["error"].lower())

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

    def test_automation_key_can_fetch_sender_output_and_update_sent_state(self):
        self.client.application.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.logout()

        sender_response = self.client.get(
            "/api/emails/weeks/2026-03-09/sender-output",
            headers={"X-Automation-Key": "secret-key", "X-Email-Actor": "google-apps-script"},
        )
        self.assertEqual(sender_response.status_code, 200)

        claim_response = self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Automation-Key": "secret-key", "X-Email-Actor": "google-apps-script"},
        )
        self.assertEqual(claim_response.status_code, 200)
        claim_payload = claim_response.get_json()
        assert claim_payload is not None
        self.assertTrue(claim_payload["sent"]["sending"])

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

    def test_save_week_rejects_send_locked_week(self):
        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve", headers={"X-Email-Actor": "reviewer"})
        self.client.post(
            "/api/emails/weeks/2026-03-09/sent",
            json={"state": "sending"},
            headers={"X-Email-Actor": "sender-bot"},
        )

        response = self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "heading": "Edited", "events": []},
        )

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        assert payload is not None
        self.assertIn("mark it unsent", payload["error"].lower())

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

    def test_approving_event_request_adds_custom_event_and_resets_approval(self):
        request_response = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Admissions Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "time_text": "6:00 PM",
                "location": "Welcome Center",
                "category": "Admissions",
                "description": "Meet the coaches and tour the campus.",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            },
        )
        request_payload = request_response.get_json()
        assert request_payload is not None
        request_id = request_payload["request"]["request_id"]

        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={"start_date": "2026-03-09", "end_date": "2026-03-15", "events": []},
        )
        self.client.post("/api/emails/weeks/2026-03-09/approve")

        response = self.client.post(
            f"/api/emails/weeks/2026-03-09/requests/{request_id}/approve",
            json={"reviewer_notes": "Looks good for this week."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["request"]["status"], "approved")
        self.assertEqual(payload["request"]["review"]["decision"], "approved")
        self.assertEqual(payload["request"]["review"]["resolved_event_id"], f"request-{request_id}")
        self.assertFalse(payload["week"]["approval"]["approved"])
        self.assertEqual(payload["week"]["events"][0]["source"], "custom")
        self.assertEqual(payload["week"]["events"][0]["metadata"]["request_id"], request_id)

    def test_approving_event_request_rolls_back_week_if_review_write_fails(self):
        self.client.application.config["EMAILS_REQUEST_STORE"] = _FailingReviewRequestStore()
        failing_store = self.client.application.config["EMAILS_REQUEST_STORE"]
        request_record = failing_store.submit_request(
            {
                "title": "Admissions Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "time_text": "6:00 PM",
                "location": "Welcome Center",
                "category": "Admissions",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )

        self.client.put(
            "/api/emails/weeks/2026-03-09",
            json={
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "Original Heading",
                "events": [],
            },
        )

        response = self.client.post(
            f"/api/emails/weeks/2026-03-09/requests/{request_record.request_id}/approve",
            json={"reviewer_notes": "Looks good for this week."},
        )

        self.assertEqual(response.status_code, 503)
        week_response = self.client.get("/api/emails/weeks/2026-03-09")
        self.assertEqual(week_response.status_code, 200)
        week_payload = week_response.get_json()
        assert week_payload is not None
        self.assertEqual(week_payload["week"]["events"], [])

    def test_denying_event_request_records_review_without_creating_event(self):
        request_response = self.client.post(
            "/api/emails/requests",
            json={
                "title": "Film Club Note",
                "start_date": "2026-03-10",
                "end_date": "2026-03-10",
                "time_text": "3:30 PM",
                "location": "Screening Room",
                "category": "Club",
                "requester_name": "Morgan Lee",
                "requester_email": "morgan@kentdenver.org",
            },
        )
        request_payload = request_response.get_json()
        assert request_payload is not None
        request_id = request_payload["request"]["request_id"]

        response = self.client.post(
            f"/api/emails/weeks/2026-03-09/requests/{request_id}/deny",
            json={"reviewer_notes": "This is outside the sports email scope."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["request"]["status"], "denied")
        self.assertEqual(payload["request"]["review"]["decision"], "denied")

        week_response = self.client.get("/api/emails/weeks/2026-03-09")
        self.assertEqual(week_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
