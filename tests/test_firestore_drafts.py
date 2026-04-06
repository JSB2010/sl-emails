import unittest
from unittest.mock import Mock, patch

from sl_emails.contracts.firestore_week_shape import (
    EMAIL_WEEKS_COLLECTION,
    EVENTS_SUBCOLLECTION,
    build_week_draft_document,
)
from sl_emails.ingest import firestore_drafts as ingest_firestore_drafts
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore
from tests.fixtures import FakeArtsEvent, FakeGame


class FakeSnapshot:
    def __init__(self, payload=None, *, exists=True):
        self._payload = payload or {}
        self.exists = exists

    def to_dict(self):
        return self._payload


class FakeEventsCollection:
    def __init__(self, documents):
        self._documents = [FakeSnapshot(document) for document in documents]

    def stream(self):
        return list(self._documents)


class FakeWeekDocument:
    def __init__(self, week_payload, event_payloads):
        self._week_payload = week_payload
        self._event_payloads = event_payloads

    def get(self):
        return FakeSnapshot(self._week_payload, exists=True)

    def collection(self, name):
        if name != EVENTS_SUBCOLLECTION:
            raise AssertionError(f"Unexpected collection: {name}")
        return FakeEventsCollection(self._event_payloads)


class FakeWeeksCollection:
    def __init__(self, week_payload, event_payloads):
        self._week_payload = week_payload
        self._event_payloads = event_payloads

    def document(self, week_id):
        if week_id != self._week_payload["start_date"]:
            return FakeWeekDocument({}, [])
        return FakeWeekDocument(self._week_payload, self._event_payloads)


class FakeFirestoreClient:
    def __init__(self, week_payload, event_payloads):
        self._week_payload = week_payload
        self._event_payloads = event_payloads

    def collection(self, name):
        if name != EMAIL_WEEKS_COLLECTION:
            raise AssertionError(f"Unexpected root collection: {name}")
        return FakeWeeksCollection(self._week_payload, self._event_payloads)


class FirestoreDraftTests(unittest.TestCase):
    def test_build_week_draft_document_normalizes_source_events(self):
        document = build_week_draft_document(
            start_date="2026-03-09",
            end_date="2026-03-15",
            events=[FakeArtsEvent(), FakeGame()],
            summary={"sportsGames": 1, "artsEvents": 1, "totalEvents": 2},
            run_context={"githubRunId": "12345", "githubSha": "abc123"},
            is_middle_school_game=lambda team: "middle school" in team.lower(),
            is_varsity_game=lambda team: "varsity" in team.lower(),
        )

        self.assertEqual(document["weekKey"], "2026-03-09")
        self.assertEqual(document["week"]["status"], "draft")
        self.assertEqual(document["week"]["start_date"], "2026-03-09")
        self.assertEqual(document["week"]["source_summary"]["totalEvents"], 2)
        self.assertEqual(document["week"]["delivery"]["mode"], "default")
        self.assertEqual(document["week"]["delivery"]["send_on"], "2026-03-08")
        self.assertEqual(document["week"]["copy_overrides"]["hero_text"], "")
        self.assertEqual(len(document["events"]), 2)
        self.assertEqual(document["events"][0]["audiences"], ["middle-school"])
        self.assertEqual(document["events"][0]["source"], "athletics")
        self.assertEqual(document["events"][0]["kind"], "game")
        self.assertEqual(document["events"][1]["source"], "arts")
        self.assertEqual(document["events"][1]["badge"], "EVENT")
        self.assertEqual(document["events"][1]["kind"], "event")

    def test_ingest_document_round_trips_through_backend_firestore_store(self):
        document = build_week_draft_document(
            start_date="2026-03-09",
            end_date="2026-03-15",
            events=[FakeArtsEvent(), FakeGame()],
            summary={"sportsGames": 1, "artsEvents": 1, "totalEvents": 2},
            run_context={"githubRunId": "12345", "githubSha": "abc123"},
            is_middle_school_game=lambda team: "middle school" in team.lower(),
            is_varsity_game=lambda team: "varsity" in team.lower(),
        )

        store = FirestoreWeeklyEmailStore()
        store._client = FakeFirestoreClient(document["week"], document["events"])

        week = store.get_week("2026-03-09")

        assert week is not None
        self.assertEqual(week.start_date, "2026-03-09")
        self.assertEqual(week.end_date, "2026-03-15")
        self.assertEqual(week.status, "draft")
        self.assertEqual(len(week.events), 2)
        self.assertEqual(week.events[0].audiences, ["middle-school"])
        self.assertEqual(week.events[0].source, "athletics")
        self.assertEqual(week.events[1].source, "arts")
        self.assertEqual(week.events[1].kind, "event")
        self.assertFalse(week.approval["approved"])

    @patch("sl_emails.ingest.firestore_drafts.requests.delete")
    @patch("sl_emails.ingest.firestore_drafts.requests.get")
    @patch("sl_emails.ingest.firestore_drafts.requests.patch")
    def test_upsert_week_draft_patches_week_and_event_documents(self, mock_patch, mock_get, mock_delete):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        mock_get_response = Mock()
        mock_get_response.ok = True
        mock_get_response.status_code = 200
        mock_get_response.text = ""
        mock_get_response.json.return_value = {
            "documents": [
                {"name": "projects/kent-denver-project/databases/(default)/documents/emailWeeks/2026-03-09/events/current-event"},
                {"name": "projects/kent-denver-project/databases/(default)/documents/emailWeeks/2026-03-09/events/stale-event"},
            ]
        }
        mock_get.return_value = mock_get_response

        mock_delete_response = Mock()
        mock_delete_response.ok = True
        mock_delete_response.status_code = 200
        mock_delete_response.text = ""
        mock_delete.return_value = mock_delete_response

        document = {
            "weekKey": "2026-03-09",
            "week": {
                "start_date": "2026-03-09",
                "end_date": "2026-03-15",
                "heading": "This Week at Kent Denver",
                "status": "draft",
                "approval": {"approved": False, "approved_at": "", "approved_by": ""},
                "sent": {"sent": False, "sent_at": "", "sent_by": "", "sending": False, "sending_at": "", "sending_by": ""},
                "notes": "",
                "delivery": {"mode": "default", "send_on": "2026-03-08", "send_time": "16:00", "updated_at": "", "updated_by": ""},
                "copy_overrides": {"hero_text": "", "intro_title": "", "intro_text": "", "spotlight_label": "", "schedule_label": "", "also_on_schedule_label": "", "empty_day_template": "", "cta_eyebrow": "", "cta_title": "", "cta_text": ""},
            },
            "events": [
                {
                    "id": "current-event",
                    "title": "Middle School Volleyball",
                    "start_date": "2026-03-10",
                    "end_date": "2026-03-10",
                    "time_text": "4:00 PM",
                    "location": "Kent Denver Gym",
                    "category": "Volleyball",
                    "source": "athletics",
                    "audiences": ["middle-school"],
                    "kind": "game",
                    "subtitle": "vs. Front Range",
                    "description": "",
                    "link": "",
                    "badge": "HOME",
                    "priority": 4,
                    "accent": "#0066ff",
                    "source_id": "current-event",
                    "status": "active",
                    "team": "Middle School Volleyball",
                    "opponent": "Front Range",
                    "is_home": True,
                    "metadata": {"school_bucket": "middle_school"},
                    "created_at": "2026-03-01T12:00:00Z",
                    "updated_at": "2026-03-01T12:00:00Z",
                }
            ],
        }

        document_name = ingest_firestore_drafts.upsert_week_draft(
            document=document,
            access_token="token-123",
            project_id="kent-denver-project",
        )

        self.assertEqual(
            document_name,
            "projects/kent-denver-project/databases/(default)/documents/emailWeeks/2026-03-09",
        )
        self.assertEqual(mock_patch.call_count, 2)
        week_patch_kwargs = mock_patch.call_args_list[0].kwargs
        event_patch_kwargs = mock_patch.call_args_list[1].kwargs
        self.assertEqual(week_patch_kwargs["headers"]["Authorization"], "Bearer token-123")
        self.assertIn(("updateMask.fieldPaths", "start_date"), week_patch_kwargs["params"])
        self.assertTrue(event_patch_kwargs["json"]["name"].endswith("/events/current-event"))
        self.assertIn(("updateMask.fieldPaths", "audiences"), event_patch_kwargs["params"])
        mock_get.assert_called_once()
        mock_delete.assert_called_once()
        self.assertTrue(mock_delete.call_args.args[0].endswith("/events/stale-event"))


if __name__ == "__main__":
    unittest.main()
