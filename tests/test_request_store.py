import unittest

from sl_emails.services.request_store import MemoryEventRequestStore


class MemoryEventRequestStoreTests(unittest.TestCase):
    def test_submit_request_normalizes_week_and_review_state(self):
        store = MemoryEventRequestStore()

        record = store.submit_request(
            {
                "title": "Senior Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "Jordan@KentDenver.org",
            }
        )

        self.assertEqual(record.week_id, "2026-03-09")
        self.assertEqual(record.status, "pending")
        self.assertEqual(record.requester_email, "jordan@kentdenver.org")
        self.assertEqual(record.review["decision"], "")

    def test_review_request_requires_pending_status(self):
        store = MemoryEventRequestStore()
        record = store.submit_request(
            {
                "title": "Senior Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )

        store.review_request(record.week_id, record.request_id, decision="approved", reviewed_by="reviewer")

        with self.assertRaises(ValueError):
            store.review_request(record.week_id, record.request_id, decision="denied", reviewed_by="reviewer")


if __name__ == "__main__":
    unittest.main()
