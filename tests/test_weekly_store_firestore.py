import unittest
from unittest.mock import patch

from sl_emails.contracts.firestore_week_shape import EMAIL_WEEKS_COLLECTION, EVENTS_SUBCOLLECTION, build_week_draft_document
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore
from tests.fixtures import FakeArtsEvent, FakeGame


class _FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if isinstance(self._data, dict) else {}


class _FakeEventsCollection:
    def __init__(self, event_docs):
        self._event_docs = event_docs

    def stream(self):
        return [_FakeSnapshot(doc) for doc in self._event_docs]


class _FakeWeekRef:
    def __init__(self, week_doc, event_docs):
        self._week_doc = week_doc
        self._event_docs = event_docs

    def get(self):
        return _FakeSnapshot(self._week_doc)

    def collection(self, name):
        if name != EVENTS_SUBCOLLECTION:
            raise AssertionError(f"unexpected subcollection: {name}")
        return _FakeEventsCollection(self._event_docs)


class _FakeWeeksCollection:
    def __init__(self, week_docs):
        self._week_docs = week_docs

    def document(self, week_id):
        payload = self._week_docs.get(week_id)
        if payload is None:
            return _FakeWeekRef(None, [])
        return _FakeWeekRef(payload["week"], payload["events"])


class _FakeFirestoreClient:
    def __init__(self, week_docs, *, expected_collection=EMAIL_WEEKS_COLLECTION):
        self._week_docs = week_docs
        self._expected_collection = expected_collection

    def collection(self, name):
        if name != self._expected_collection:
            raise AssertionError(f"unexpected collection: {name}")
        return _FakeWeeksCollection(self._week_docs)


class FirestoreWeeklyEmailStoreContractTests(unittest.TestCase):
    def test_get_week_hydrates_ingest_firestore_shape(self):
        ingest_document = build_week_draft_document(
            start_date="2026-03-09",
            end_date="2026-03-15",
            events=[FakeArtsEvent(), FakeGame()],
            summary={"sportsGames": 1, "artsEvents": 1, "totalEvents": 2},
            run_context={"githubRunId": "12345", "githubSha": "abc123"},
            is_middle_school_game=lambda team: "middle school" in team.lower(),
            is_varsity_game=lambda team: "varsity" in team.lower(),
        )

        store = FirestoreWeeklyEmailStore()
        store._client = _FakeFirestoreClient(
            {
                "2026-03-09": {
                    "week": ingest_document["week"],
                    "events": list(reversed(ingest_document["events"])),
                }
            }
        )

        week = store.get_week("2026-03-09")

        self.assertIsNotNone(week)
        assert week is not None
        self.assertEqual(week.week_id, "2026-03-09")
        self.assertEqual(week.start_date, "2026-03-09")
        self.assertEqual(week.end_date, "2026-03-15")
        self.assertEqual(week.status, "draft")
        self.assertEqual(week.approval, {"approved": False, "approved_at": "", "approved_by": ""})
        self.assertEqual(week.sent, {"sent": False, "sent_at": "", "sent_by": "", "sending": False, "sending_at": "", "sending_by": ""})
        self.assertEqual(week.heading, ingest_document["week"]["heading"])
        self.assertEqual([event.id for event in week.events], [item["id"] for item in ingest_document["events"]])
        self.assertEqual([event.title for event in week.events], ["Middle School Volleyball", "Spring Concert"])
        self.assertEqual(week.events[0].audiences, ["middle-school"])
        self.assertEqual(week.events[0].kind, "game")
        self.assertEqual(week.events[1].source, "arts")
        self.assertEqual(week.events[1].kind, "event")

    def test_collection_name_defaults_from_environment(self):
        with patch.dict("os.environ", {"FIRESTORE_COLLECTION": "stagingEmailWeeks"}, clear=False):
            store = FirestoreWeeklyEmailStore()
            store._client = _FakeFirestoreClient({}, expected_collection="stagingEmailWeeks")

            self.assertEqual(store.collection_name, "stagingEmailWeeks")
            self.assertIsNone(store.get_week("2026-03-09"))


if __name__ == "__main__":
    unittest.main()