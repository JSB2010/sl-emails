import unittest

from sl_emails.services.activity_log import EmailActivityRecord, FirestoreActivityLogStore, MemoryActivityLogStore


class _FakeSnapshot:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return dict(self._payload)


class _FakeDocumentRef:
    def __init__(self, store, document_id):
        self._store = store
        self._document_id = document_id

    def set(self, payload):
        self._store[self._document_id] = dict(payload)


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(self._store, document_id)

    def stream(self):
        return [_FakeSnapshot(value) for value in self._store.values()]


class _FakeClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return _FakeCollection(self.collections.setdefault(name, {}))


class _FakeWeeklyStore:
    def __init__(self, client):
        self._client = client

    def _get_client(self):
        return self._client


class ActivityLogTests(unittest.TestCase):
    def test_email_activity_record_defaults_and_memory_store_sorting(self):
        record = EmailActivityRecord(event_type="send", status="success", actor="bot")
        payload = record.to_dict()
        self.assertTrue(payload["occurred_at"])
        self.assertTrue(payload["activity_id"])

        store = MemoryActivityLogStore()
        store.log(event_type="scheduled_ingest", status="success", actor="bot", week_id="2026-03-09")
        store.log(event_type="send", status="success", actor="bot", week_id="2026-03-09")
        store.log(event_type="other", status="success", actor="bot", week_id="2026-03-16")

        recent = store.list_recent(week_id="2026-03-09", limit=10)
        self.assertEqual(len(recent), 2)
        self.assertEqual({item.week_id for item in recent}, {"2026-03-09"})

    def test_firestore_activity_log_store_round_trips(self):
        client = _FakeClient()
        store = FirestoreActivityLogStore()
        store._weekly_store = _FakeWeeklyStore(client)

        created = store.log(
            event_type="send",
            status="success",
            actor="bot",
            week_id="2026-03-09",
            message="Delivered email",
            details={"state": "sent"},
        )
        recent = store.list_recent(week_id="2026-03-09", limit=5)

        self.assertEqual(created.week_id, "2026-03-09")
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].details["state"], "sent")


if __name__ == "__main__":
    unittest.main()
