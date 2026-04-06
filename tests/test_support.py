import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from flask import session

from sl_emails.services.activity_log import MemoryActivityLogStore
from sl_emails.services.admin_settings import MemoryAdminSettingsStore
from sl_emails.services.request_store import MemoryEventRequestStore
from sl_emails.services.signage_store import MemorySignageStore
from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app
from sl_emails.web import support as web_support


class _FailingActivityStore(MemoryActivityLogStore):
    def log(self, *args, **kwargs):
        raise RuntimeError("activity unavailable")


class _FailingWeeklyStore(MemoryWeeklyEmailStore):
    def update_week_metadata(self, week_id, metadata):
        raise RuntimeError("week metadata unavailable")


class _FailingSignageStore(MemorySignageStore):
    def update_day_metadata(self, day_id, metadata):
        raise RuntimeError("signage metadata unavailable")


class WebSupportTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SESSION_COOKIE_SECURE": False,
                "EMAILS_STORE": MemoryWeeklyEmailStore(),
                "SIGNAGE_STORE": MemorySignageStore(),
                "EMAILS_REQUEST_STORE": MemoryEventRequestStore(),
                "EMAILS_SETTINGS_STORE": MemoryAdminSettingsStore(),
                "EMAILS_ACTIVITY_STORE": MemoryActivityLogStore(),
            }
        )

    def test_bootstrap_email_helpers_use_explicit_and_fallback_values(self):
        with self.app.app_context():
            self.app.config["EMAILS_BOOTSTRAP_ALLOWED_EMAILS"] = "Admin@KentDenver.org, studentleader@kentdenver.org"
            self.app.config["EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS"] = ""

            self.assertEqual(
                web_support.bootstrap_admin_emails(),
                ["admin@kentdenver.org", "studentleader@kentdenver.org"],
            )
            self.assertEqual(
                web_support.bootstrap_notification_emails(),
                ["admin@kentdenver.org", "studentleader@kentdenver.org"],
            )

            self.app.config["EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS"] = "ops@kentdenver.org"
            self.assertEqual(web_support.bootstrap_notification_emails(), ["ops@kentdenver.org"])

    def test_request_protector_switches_between_public_and_firestore_modes(self):
        with self.app.app_context():
            protector = web_support.get_request_protector()
            self.assertEqual(protector.__class__.__name__, "PublicRequestProtector")

            self.app.config["TESTING"] = False
            self.app.config["EMAILS_LOCAL_DEV"] = ""
            self.app.config.pop("EMAILS_REQUEST_PROTECTOR", None)
            with patch.object(web_support, "FirestoreRequestProtector") as mock_protector:
                sentinel = object()
                mock_protector.return_value = sentinel
                self.assertIs(web_support.get_request_protector(), sentinel)

    def test_signage_time_helpers_and_cache_control_cover_rollover_cases(self):
        now = datetime(2026, 4, 3, 0, 15, tzinfo=ZoneInfo("America/Denver"))
        later = datetime(2026, 4, 3, 6, 0, tzinfo=ZoneInfo("America/Denver"))

        self.assertEqual(web_support._seconds_until_next_signage_midnight(now), 85500)
        self.assertEqual(web_support._seconds_until_signage_rollover_deadline(now), 9900)
        self.assertEqual(web_support._signage_rollover_fallback_day_id("2026-04-03", now), "2026-04-02")
        self.assertIsNone(web_support._signage_rollover_fallback_day_id("2026-04-02", now))
        self.assertIsNone(web_support._signage_rollover_fallback_day_id("2026-04-03", later))
        self.assertEqual(web_support._signage_cache_control("2026-04-02"), "no-store, max-age=0")

        with patch.object(web_support, "_seconds_until_signage_rollover_deadline", return_value=120):
            self.assertEqual(
                web_support._signage_cache_control(None, fallback_served=True),
                "public, max-age=120, s-maxage=120",
            )
        with patch.object(web_support, "_seconds_until_next_signage_midnight", return_value=43200):
            self.assertEqual(
                web_support._signage_cache_control(None, fallback_served=False),
                "public, max-age=43200, s-maxage=43200",
            )

    def test_request_and_auth_helpers_use_request_context(self):
        with self.app.test_request_context("/emails?week=2026-03-09"):
            session["auth_user"] = {"email": "AppDev@KentDenver.org", "name": "App Dev"}
            self.app.config["PUBLIC_BASE_URL"] = ""

            self.assertEqual(web_support.current_user_email(), "appdev@kentdenver.org")
            self.assertEqual(web_support.current_public_base_url(), "https://localhost")
            self.assertEqual(web_support._request_next_url(), "/emails?week=2026-03-09")
            urls = web_support.auth_urls()
            self.assertIn("/login?next=/emails?week=2026-03-09", urls["login"])
            self.assertEqual(urls["logout"], "/logout")

            self.app.config["PUBLIC_BASE_URL"] = "https://emails.kentdenver.org/"
            self.assertEqual(web_support.current_public_base_url(), "https://emails.kentdenver.org")

    def test_automation_key_validation_checks_configured_secret(self):
        with self.app.test_request_context("/api/emails/automation/settings", headers={"X-Automation-Key": "secret-key"}):
            self.app.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
            self.assertTrue(web_support.has_valid_automation_key())

        with self.app.test_request_context("/api/emails/automation/settings", headers={"X-Automation-Key": "wrong"}):
            self.app.config["EMAILS_AUTOMATION_KEY"] = "secret-key"
            self.assertFalse(web_support.has_valid_automation_key())

    def test_safe_metadata_and_activity_updates_swallow_store_failures(self):
        with self.app.app_context():
            self.app.config["EMAILS_ACTIVITY_STORE"] = _FailingActivityStore()
            self.app.config["EMAILS_STORE"] = _FailingWeeklyStore()
            self.app.config["SIGNAGE_STORE"] = _FailingSignageStore()

            with patch.object(self.app.logger, "exception") as mock_exception:
                web_support.write_activity(event_type="send", status="failed", actor="bot")
                self.assertIsNone(web_support.update_week_metadata_safely("2026-03-09", {"send": {"status": "failed"}}))
                self.assertIsNone(web_support.update_signage_metadata_safely("2026-03-23", {"ingest": {"status": "failed"}}))

            self.assertGreaterEqual(mock_exception.call_count, 3)


if __name__ == "__main__":
    unittest.main()
