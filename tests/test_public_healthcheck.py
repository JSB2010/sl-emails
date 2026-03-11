import unittest

from sl_emails.services.weekly_store import MemoryWeeklyEmailStore
from sl_emails.web import create_app


class PublicHealthcheckTests(unittest.TestCase):
    def test_public_healthcheck(self):
        app = create_app({"TESTING": True, "EMAILS_STORE": MemoryWeeklyEmailStore()})

        response = app.test_client().get("/_health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()