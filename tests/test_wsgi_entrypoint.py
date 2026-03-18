import unittest
from importlib import import_module, reload
from unittest.mock import patch


class WsgiEntrypointTests(unittest.TestCase):
    def test_wsgi_entrypoint_serves_public_healthcheck(self):
        with patch.dict(
            "os.environ",
            {
                "EMAILS_SESSION_SECRET": "test-secret",
                "EMAILS_AUTOMATION_KEY": "test-automation-key",
                "GOOGLE_OAUTH_CLIENT_ID": "client-id",
                "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
                "GOOGLE_OAUTH_CALLBACK_URL": "https://example.test/auth/google/callback",
            },
            clear=False,
        ):
            wsgi_module = reload(import_module("sl_emails.web.wsgi"))
            wsgi_app = wsgi_module.app
        response = wsgi_app.test_client().get("/_health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
