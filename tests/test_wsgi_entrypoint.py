import unittest

from sl_emails.web.wsgi import app as wsgi_app


class WsgiEntrypointTests(unittest.TestCase):
    def test_wsgi_entrypoint_serves_public_healthcheck(self):
        response = wsgi_app.test_client().get("/_health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()