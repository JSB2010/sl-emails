import unittest

from sl_emails.services.request_store import (
    MemoryEventRequestStore,
    event_payload_for_request,
    normalize_request_payload,
)


class MemoryEventRequestStoreTests(unittest.TestCase):
    def test_normalize_request_payload_fills_defaults_and_uses_date_alias(self):
        record = normalize_request_payload(
            {
                "kind": "game",
                "date": "2026-03-12",
                "team": "Girls Soccer - Varsity",
                "audience": "upper-school",
                "requester_name": "Jordan Smith",
                "requester_email": "Jordan@KentDenver.org",
            }
        )

        self.assertEqual(record.week_id, "2026-03-09")
        self.assertEqual(record.title, "Girls Soccer - Varsity")
        self.assertEqual(record.team, "Girls Soccer - Varsity")
        self.assertEqual(record.time_text, "TBA")
        self.assertEqual(record.location, "On Campus")
        self.assertEqual(record.category, "School Event")
        self.assertEqual(record.requester_email, "jordan@kentdenver.org")

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

    def test_event_payload_for_request_carries_request_metadata_forward(self):
        store = MemoryEventRequestStore()
        record = store.submit_request(
            {
                "title": "Senior Night",
                "start_date": "2026-03-12",
                "end_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
                "requester_notes": "Please include the volunteer link.",
            }
        )

        payload = event_payload_for_request(record)

        self.assertEqual(payload["id"], f"request-{record.request_id}")
        self.assertEqual(payload["metadata"]["request_id"], record.request_id)
        self.assertEqual(payload["metadata"]["requested_by_email"], "jordan@kentdenver.org")
        self.assertEqual(payload["metadata"]["requester_notes"], "Please include the volunteer link.")

    def test_normalize_request_payload_rejects_invalid_ranges_and_bad_email(self):
        with self.assertRaises(ValueError):
            normalize_request_payload(
                {
                    "title": "Senior Night",
                    "start_date": "2026-03-13",
                    "end_date": "2026-03-12",
                    "requester_name": "Jordan Smith",
                    "requester_email": "jordan@kentdenver.org",
                }
            )

        with self.assertRaises(ValueError):
            normalize_request_payload(
                {
                    "title": "Senior Night",
                    "start_date": "2026-03-12",
                    "requester_name": "Jordan Smith",
                    "requester_email": "not-an-email",
                }
            )

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

    def test_normalize_request_payload_preserves_existing_values_on_partial_update(self):
        existing = normalize_request_payload(
            {
                "request_id": "request-1",
                "title": "Community Night",
                "start_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
                "metadata": {"source": "form"},
            }
        )
        existing.status = "approved"
        existing.review = {"decision": "approved", "reviewed_by": "reviewer"}

        updated = normalize_request_payload({"title": "Updated Community Night"}, existing=existing)

        self.assertEqual(updated.request_id, "request-1")
        self.assertEqual(updated.requester_email, "jordan@kentdenver.org")
        self.assertEqual(updated.metadata["source"], "form")
        self.assertEqual(updated.status, "approved")
        self.assertEqual(updated.review["decision"], "approved")

    def test_memory_store_get_list_and_review_cover_missing_and_invalid_paths(self):
        store = MemoryEventRequestStore()
        second = store.submit_request(
            {
                "title": "B Event",
                "start_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )
        first = store.submit_request(
            {
                "title": "A Event",
                "start_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )
        store.review_request(second.week_id, second.request_id, decision="approved", reviewed_by="reviewer")

        listed = store.list_requests("2026-03-09")
        self.assertEqual([item.title for item in listed], ["A Event", "B Event"])
        self.assertIsNone(store.get_request("2026-03-09", "missing"))

        with self.assertRaises(KeyError):
            store.review_request("2026-03-09", "missing", decision="approved", reviewed_by="reviewer")
        with self.assertRaises(ValueError):
            store.review_request(first.week_id, first.request_id, decision="maybe", reviewed_by="reviewer")


if __name__ == "__main__":
    unittest.main()
