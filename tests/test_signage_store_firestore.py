import unittest

from sl_emails.services.signage_store import FirestoreSignageStore, SIGNAGE_DAYS_COLLECTION


class _FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if isinstance(self._data, dict) else {}


class _FakeDayRef:
    def __init__(self, payload):
        self._payload = payload

    def get(self):
        return _FakeSnapshot(self._payload)


class _FakeDaysCollection:
    def __init__(self, day_docs):
        self._day_docs = day_docs

    def document(self, day_id):
        return _FakeDayRef(self._day_docs.get(day_id))


class _FakeFirestoreClient:
    def __init__(self, day_docs, *, expected_collection=SIGNAGE_DAYS_COLLECTION):
        self._day_docs = day_docs
        self._expected_collection = expected_collection

    def collection(self, name):
        if name != self._expected_collection:
            raise AssertionError(f"unexpected collection: {name}")
        return _FakeDaysCollection(self._day_docs)


class FirestoreSignageStoreContractTests(unittest.TestCase):
    def test_get_day_hydrates_firestore_shape(self):
        store = FirestoreSignageStore()
        store._client = _FakeFirestoreClient(
            {
                "2026-03-23": {
                    "date": "2026-03-23",
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
                    "metadata": {"ingest": {"status": "success", "action": "created"}},
                    "created_at": "2026-03-23T06:00:00Z",
                    "updated_at": "2026-03-23T06:00:00Z",
                }
            }
        )

        day = store.get_day("2026-03-23")

        self.assertIsNotNone(day)
        assert day is not None
        self.assertEqual(day.day_id, "2026-03-23")
        self.assertEqual(day.source_summary["athletics_events"], 1)
        self.assertEqual(day.source_summary["total_events"], 1)
        self.assertEqual(day.metadata["ingest"]["action"], "created")
        self.assertEqual(day.events[0].title, "Varsity Soccer")
        self.assertEqual(day.events[0].team, "Varsity Soccer")

    def test_collection_name_can_be_overridden(self):
        store = FirestoreSignageStore(collection_name="stagingSignageDays")
        store._client = _FakeFirestoreClient({}, expected_collection="stagingSignageDays")

        self.assertEqual(store.collection_name, "stagingSignageDays")
        self.assertIsNone(store.get_day("2026-03-23"))


if __name__ == "__main__":
    unittest.main()
