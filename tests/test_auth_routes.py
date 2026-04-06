import unittest
from unittest.mock import patch

from flask import redirect

from sl_emails.services.activity_log import MemoryActivityLogStore
from sl_emails.services.admin_settings import MemoryAdminSettingsStore
from sl_emails.services.request_store import MemoryEventRequestStore
from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app


class _FakeGoogleClient:
    def __init__(self):
        self.redirect_uri = ""
        self.token = {}
        self.error = None

    def authorize_redirect(self, redirect_uri):
        self.redirect_uri = redirect_uri
        return redirect(f"https://accounts.google.com/o/oauth2/auth?redirect_uri={redirect_uri}")

    def authorize_access_token(self):
        if self.error is not None:
            raise self.error
        return self.token


class _FakeOAuth:
    def __init__(self):
        self.google = _FakeGoogleClient()


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app(
            {
                "TESTING": True,
                "SESSION_COOKIE_SECURE": False,
                "GOOGLE_OAUTH_CALLBACK_URL": "https://example.test/auth/google/callback",
                "EMAILS_STORE": MemoryWeeklyEmailStore(),
                "EMAILS_REQUEST_STORE": MemoryEventRequestStore(),
                "EMAILS_SETTINGS_STORE": MemoryAdminSettingsStore(),
                "EMAILS_ACTIVITY_STORE": MemoryActivityLogStore(),
            }
        )
        self.client = app.test_client()

    def test_google_start_returns_503_when_oauth_is_not_configured(self):
        with patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=False):
            response = self.client.get("/auth/google/start?next=/emails/settings")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Google sign-in is not configured", response.get_data(as_text=True))

    def test_google_start_stashes_next_and_uses_configured_callback(self):
        fake_oauth = _FakeOAuth()
        with (
            patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=True),
            patch("sl_emails.web.routes.auth.oauth", fake_oauth),
        ):
            response = self.client.get("/auth/google/start?next=/emails/settings")

        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com", response.headers["Location"])
        self.assertEqual(fake_oauth.google.redirect_uri, "https://example.test/auth/google/callback")
        with self.client.session_transaction() as session:
            self.assertEqual(session["auth_next"], "/emails/settings")

    def test_google_callback_redirects_allowlisted_user_to_saved_next_url(self):
        fake_oauth = _FakeOAuth()
        fake_oauth.google.token = {
            "userinfo": {
                "email": "appdev@kentdenver.org",
                "name": "App Dev",
                "picture": "https://example.test/avatar.png",
            }
        }
        with self.client.session_transaction() as session:
            session["auth_next"] = "/emails/settings"

        with (
            patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=True),
            patch("sl_emails.web.routes.auth.oauth", fake_oauth),
        ):
            response = self.client.get("/auth/google/callback")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/emails/settings")
        with self.client.session_transaction() as session:
            self.assertEqual(session["auth_user"]["email"], "appdev@kentdenver.org")

    def test_login_redirects_signed_in_users_based_on_allowlist(self):
        with self.client.session_transaction() as session:
            session["auth_user"] = {"email": "appdev@kentdenver.org", "name": "App Dev"}
        response = self.client.get("/login?next=/emails/settings")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/emails/settings")

        with self.client.session_transaction() as session:
            session["auth_user"] = {"email": "outsider@kentdenver.org", "name": "Outside User"}
        response = self.client.get("/login?next=/emails/settings")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/access-denied")

    def test_google_callback_redirects_non_allowlisted_user_to_access_denied(self):
        fake_oauth = _FakeOAuth()
        fake_oauth.google.token = {
            "userinfo": {
                "email": "outsider@kentdenver.org",
                "name": "Outside User",
            }
        }
        with self.client.session_transaction() as session:
            session["auth_next"] = "/emails"

        with (
            patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=True),
            patch("sl_emails.web.routes.auth.oauth", fake_oauth),
        ):
            response = self.client.get("/auth/google/callback")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/access-denied")
        with self.client.session_transaction() as session:
            self.assertEqual(session["auth_user"]["email"], "outsider@kentdenver.org")

    def test_google_callback_clears_session_when_google_returns_no_email(self):
        fake_oauth = _FakeOAuth()
        fake_oauth.google.token = {"userinfo": {"name": "Missing Email"}}
        with self.client.session_transaction() as session:
            session["auth_next"] = "/emails"
            session["auth_user"] = {"email": "stale@kentdenver.org"}

        with (
            patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=True),
            patch("sl_emails.web.routes.auth.oauth", fake_oauth),
        ):
            response = self.client.get("/auth/google/callback")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        with self.client.session_transaction() as session:
            self.assertNotIn("auth_user", session)

    def test_google_callback_redirects_to_login_when_oauth_is_disabled(self):
        with patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=False):
            response = self.client.get("/auth/google/callback")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_google_callback_clears_session_when_token_exchange_fails(self):
        fake_oauth = _FakeOAuth()
        fake_oauth.google.error = RuntimeError("oauth failure")
        with self.client.session_transaction() as session:
            session["auth_next"] = "/emails"
            session["auth_user"] = {"email": "stale@kentdenver.org"}

        with (
            patch("sl_emails.web.routes.auth.google_oauth_enabled", return_value=True),
            patch("sl_emails.web.routes.auth.oauth", fake_oauth),
        ):
            response = self.client.get("/auth/google/callback")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        with self.client.session_transaction() as session:
            self.assertNotIn("auth_user", session)

    def test_logout_and_access_denied_routes(self):
        with self.client.session_transaction() as session:
            session["auth_user"] = {"email": "appdev@kentdenver.org", "name": "App Dev"}

        logout_response = self.client.get("/logout")
        denied_response = self.client.get("/access-denied")

        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(logout_response.headers["Location"], "/login")
        self.assertEqual(denied_response.status_code, 403)
        self.assertIn("Access Denied", denied_response.get_data(as_text=True))
        with self.client.session_transaction() as session:
            self.assertNotIn("auth_user", session)


if __name__ == "__main__":
    unittest.main()
