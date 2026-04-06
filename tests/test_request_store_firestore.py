import unittest
from unittest.mock import patch

from sl_emails.services import request_store as request_store_module
from sl_emails.services.request_store import FirestoreEventRequestStore


class _FakeSnapshot:
    def __init__(self, payload):
        self._payload = payload
        self.exists = payload is not None

    def to_dict(self):
        return dict(self._payload) if isinstance(self._payload, dict) else {}


class _FakeTransaction:
    def set(self, ref, payload, merge=False):
        ref.set(payload, merge=merge)


class _FakeDocumentRef:
    def __init__(self, store, document_id):
        self._store = store
        self._document_id = document_id

    def get(self, transaction=None):
        return _FakeSnapshot(self._store.get(self._document_id))

    def set(self, payload, merge=False):
        if merge and self._document_id in self._store:
            merged = dict(self._store[self._document_id])
            for key, value in payload.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
            self._store[self._document_id] = merged
        else:
            self._store[self._document_id] = dict(payload)

    def collection(self, name):
        return _FakeCollection(self._store.setdefault(name, {}))


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(self._store, document_id)

    def stream(self):
        return [_FakeSnapshot(payload) for payload in self._store.values()]


class _FakeClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return _FakeCollection(self.collections.setdefault(name, {}))

    def transaction(self):
        return _FakeTransaction()


class _FakeWeeklyStore:
    def __init__(self, client, week_collection_name="emailWeeks"):
        self._client = client
        self.collection_name = week_collection_name

    def _get_client(self):
        return self._client

    def _week_ref(self, week_id):
        return self._client.collection(self.collection_name).document(week_id)

    def get_week(self, week_id):
        payload = self._week_ref(week_id).get().to_dict()
        if not payload:
            return None
        events = payload.get("events", [])
        class _Week:
            def __init__(self, payload, events):
                self.week_id = week_id
                self.payload = payload
                self.events = events
            def to_dict(self):
                return {**self.payload, "events": list(self.events)}
        event_docs = self._week_ref(week_id).collection("events")._store.values()
        return _Week(payload, list(event_docs))


class RequestStoreFirestoreTests(unittest.TestCase):
    def _build_store(self):
        client = _FakeClient()
        weekly_store = _FakeWeeklyStore(client)
        store = FirestoreEventRequestStore()
        store._weekly_store = weekly_store
        return store, client, weekly_store

    def test_approve_request_into_week_writes_event_and_review_state(self):
        store, _client, weekly_store = self._build_store()
        week_id = "2026-03-09"
        request_payload = {
            "request_id": "request-1",
            "week_id": week_id,
            "title": "Community Night",
            "start_date": "2026-03-11",
            "end_date": "2026-03-11",
            "time_text": "6:00 PM",
            "location": "Campus Center",
            "category": "Community",
            "audiences": ["middle-school", "upper-school"],
            "requester_name": "Jordan Smith",
            "requester_email": "jordan@kentdenver.org",
            "status": "pending",
            "review": {},
        }
        weekly_store._week_ref(week_id).collection(store.subcollection_name).document("request-1").set(request_payload)

        class _FakeFirestoreModule:
            @staticmethod
            def transactional(fn):
                return fn

        with patch.object(request_store_module, "firestore", _FakeFirestoreModule):
            updated_request, updated_week = store.approve_request_into_week(
                week_id,
                "request-1",
                reviewed_by="reviewer@kentdenver.org",
                reviewer_notes="Looks good",
            )

        self.assertEqual(updated_request.status, "approved")
        self.assertEqual(updated_request.review["reviewed_by"], "reviewer@kentdenver.org")
        self.assertEqual(updated_request.review["resolved_event_id"], "request-request-1")
        week_doc = weekly_store._week_ref(week_id).get().to_dict()
        self.assertEqual(week_doc["week_id"], week_id)
        event_doc = weekly_store._week_ref(week_id).collection("events").document("request-request-1").get().to_dict()
        self.assertEqual(event_doc["source"], "custom")
        self.assertEqual(event_doc["title"], "Community Night")
        self.assertIsNotNone(updated_week)

    def test_approve_request_into_week_rejects_locked_week(self):
        store, _client, weekly_store = self._build_store()
        week_id = "2026-03-09"
        weekly_store._week_ref(week_id).set(
            {
                "week_id": week_id,
                "start_date": week_id,
                "end_date": "2026-03-15",
                "sent": {"sent": True, "sent_at": "2026-03-09T10:00:00Z", "sent_by": "bot", "sending": False, "sending_at": "", "sending_by": ""},
            }
        )
        weekly_store._week_ref(week_id).collection(store.subcollection_name).document("request-1").set(
            {
                "request_id": "request-1",
                "week_id": week_id,
                "title": "Community Night",
                "start_date": "2026-03-11",
                "end_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
                "status": "pending",
                "review": {},
            }
        )

        class _FakeFirestoreModule:
            @staticmethod
            def transactional(fn):
                return fn

        with patch.object(request_store_module, "firestore", _FakeFirestoreModule):
            with self.assertRaises(ValueError):
                store.approve_request_into_week(
                    week_id,
                    "request-1",
                    reviewed_by="reviewer@kentdenver.org",
                )

    def test_firestore_store_submit_list_and_review_cover_basic_paths(self):
        store, _client, _weekly_store = self._build_store()
        first = store.submit_request(
            {
                "title": "Community Night",
                "start_date": "2026-03-11",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )
        second = store.submit_request(
            {
                "title": "Arts Showcase",
                "start_date": "2026-03-12",
                "requester_name": "Jordan Smith",
                "requester_email": "jordan@kentdenver.org",
            }
        )

        reviewed = store.review_request(
            second.week_id,
            second.request_id,
            decision="denied",
            reviewed_by="reviewer@kentdenver.org",
            reviewer_notes="Not this week",
        )

        listed = store.list_requests("2026-03-09")
        self.assertEqual([item.title for item in listed], ["Community Night", "Arts Showcase"])
        self.assertEqual(store.get_request(first.week_id, first.request_id).title, "Community Night")
        self.assertEqual(reviewed.status, "denied")
        self.assertEqual(reviewed.review["reviewer_notes"], "Not this week")
        self.assertIsNone(store.get_request("2026-03-09", "missing"))

    def test_firestore_store_review_and_transaction_failures_raise_expected_errors(self):
        store, _client, weekly_store = self._build_store()
        week_id = "2026-03-09"

        with self.assertRaises(KeyError):
            store.review_request(week_id, "missing", decision="approved", reviewed_by="reviewer")

        pending = {
            "request_id": "request-1",
            "week_id": week_id,
            "title": "Community Night",
            "start_date": "2026-03-11",
            "end_date": "2026-03-11",
            "requester_name": "Jordan Smith",
            "requester_email": "jordan@kentdenver.org",
            "status": "approved",
            "review": {},
        }
        weekly_store._week_ref(week_id).collection(store.subcollection_name).document("request-1").set(pending)
        with self.assertRaises(ValueError):
            store.review_request(week_id, "request-1", decision="approved", reviewed_by="reviewer")
        with self.assertRaises(ValueError):
            store.review_request(week_id, "request-1", decision="maybe", reviewed_by="reviewer")

        with patch.object(request_store_module, "firestore", None):
            with self.assertRaises(RuntimeError):
                store.approve_request_into_week(week_id, "request-1", reviewed_by="reviewer")

        pending["status"] = "pending"
        weekly_store._week_ref(week_id).collection(store.subcollection_name).document("request-1").set(pending)

        class _FakeFirestoreModule:
            @staticmethod
            def transactional(fn):
                return fn

        with patch.object(request_store_module, "firestore", _FakeFirestoreModule):
            with patch.object(store, "get_request", return_value=None):
                with self.assertRaises(RuntimeError):
                    store.approve_request_into_week(week_id, "request-1", reviewed_by="reviewer")


if __name__ == "__main__":
    unittest.main()
