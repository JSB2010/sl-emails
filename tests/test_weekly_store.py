import unittest
from unittest.mock import patch

from sl_emails.config import RuntimeFirestoreConfig
from sl_emails.services import weekly_store as weekly_store_module
from sl_emails.services.weekly_store import (
    FirestoreWeeklyEmailStore,
    MemoryWeeklyEmailStore,
    assert_week_editable,
    build_blank_week_payload,
    is_send_locked,
    merge_metadata,
    normalize_event_payload,
    normalize_week_payload,
)


class _FakeSnapshot:
    def __init__(self, data, reference=None):
        self._data = data
        self.exists = data is not None
        self.reference = reference

    def to_dict(self):
        return dict(self._data) if isinstance(self._data, dict) else {}


class _FakeDocumentRef:
    def __init__(self, store, document_id):
        self._store = store
        self._document_id = document_id

    def _node(self, create=False):
        if self._document_id not in self._store and create:
            self._store[self._document_id] = {"data": None, "subcollections": {}}
        return self._store.get(self._document_id)

    def get(self, transaction=None):
        node = self._node()
        data = None if node is None else node.get("data")
        return _FakeSnapshot(data, reference=self)

    def set(self, payload, merge=False):
        node = self._node(create=True)
        existing = node.get("data")
        if merge and isinstance(existing, dict):
            merged = dict(existing)
            for key, value in payload.items():
                merged[key] = value
            node["data"] = merged
        else:
            node["data"] = dict(payload)

    def delete(self):
        self._store.pop(self._document_id, None)

    def collection(self, name):
        node = self._node(create=True)
        return _FakeCollection(node["subcollections"].setdefault(name, {}))


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(self._store, document_id)

    def stream(self):
        snapshots = []
        for document_id, node in self._store.items():
            data = node.get("data") if isinstance(node, dict) else None
            if data is not None:
                snapshots.append(_FakeSnapshot(data, reference=_FakeDocumentRef(self._store, document_id)))
        return snapshots


class _FakeBatch:
    def __init__(self):
        self._ops = []

    def create(self, ref, payload):
        self._ops.append(("create", ref, payload))

    def set(self, ref, payload):
        self._ops.append(("set", ref, payload))

    def delete(self, ref):
        self._ops.append(("delete", ref, None))

    def commit(self):
        for op, ref, payload in self._ops:
            if op == "create":
                if ref.get().exists:
                    raise weekly_store_module.AlreadyExists("document already exists")
                ref.set(payload)
            elif op == "set":
                ref.set(payload)
            elif op == "delete":
                ref.delete()


class _FakeTransaction:
    def set(self, ref, payload, merge=False):
        ref.set(payload, merge=merge)


class _FakeClient:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        return _FakeCollection(self._collections.setdefault(name, {}))

    def batch(self):
        return _FakeBatch()

    def transaction(self):
        return _FakeTransaction()


class _FakeCredentials:
    def __init__(self):
        self.certificate_payloads = []
        self.default_calls = 0

    def Certificate(self, payload):
        self.certificate_payloads.append(payload)
        return ("certificate", payload)

    def ApplicationDefault(self):
        self.default_calls += 1
        return ("adc", self.default_calls)


class _FakeFirebaseAdmin:
    def __init__(self):
        self._apps = []
        self.init_calls = []

    def initialize_app(self, credential=None, options=None):
        self.init_calls.append({"credential": credential, "options": options})
        self._apps.append(object())


class _FakeFirestoreModule:
    def __init__(self, client):
        self._client = client

    def client(self):
        return self._client

    @staticmethod
    def transactional(fn):
        return fn


class WeeklyStoreTests(unittest.TestCase):
    def _sample_event(self, **overrides):
        payload = {
            "id": "event-1",
            "title": "Community Night",
            "start_date": "2026-03-11",
            "end_date": "2026-03-11",
            "time_text": "6:00 PM",
            "location": "Campus Center",
            "category": "Community",
            "audiences": ["middle-school", "upper-school"],
        }
        payload.update(overrides)
        return payload

    def test_merge_metadata_and_send_lock_helpers(self):
        self.assertEqual(
            merge_metadata({"ingest": {"status": "success", "actor": "bot"}}, {"ingest": {"message": "ok"}}),
            {"ingest": {"status": "success", "actor": "bot", "message": "ok"}},
        )
        self.assertFalse(is_send_locked({"sent": False, "sending": False}))
        self.assertTrue(is_send_locked({"sending": True}))
        self.assertTrue(is_send_locked({"sent": True}))

    def test_normalize_event_payload_validates_and_sets_defaults(self):
        event = normalize_event_payload(
            self._sample_event(kind="game", team="Varsity Soccer", opponent="Front Range", is_home=False),
            week_start="2026-03-09",
            week_end="2026-03-15",
            force_source="athletics",
        )

        self.assertEqual(event.kind, "game")
        self.assertEqual(event.source, "athletics")
        self.assertEqual(event.badge, "AWAY")
        self.assertEqual(event.team, "Varsity Soccer")

        with self.assertRaises(ValueError):
            normalize_event_payload(
                self._sample_event(kind="bad-kind"),
                week_start="2026-03-09",
                week_end="2026-03-15",
            )

        with self.assertRaises(ValueError):
            normalize_event_payload(
                self._sample_event(start_date="2026-03-16", end_date="2026-03-16"),
                week_start="2026-03-09",
                week_end="2026-03-15",
            )

    def test_normalize_week_payload_sorts_events_and_normalizes_delivery(self):
        payload = build_blank_week_payload("2026-03-09")
        payload["events"] = [
            self._sample_event(id="later", title="Later", time_text="7:00 PM"),
            self._sample_event(id="earlier", title="Earlier", time_text="4:00 PM"),
        ]
        payload["delivery"] = {"mode": "postpone", "send_on": "2026-03-12", "send_time": "17:00"}

        week = normalize_week_payload("2026-03-09", payload)

        self.assertEqual([event.id for event in week.events], ["earlier", "later"])
        self.assertEqual(week.delivery["mode"], "postpone")
        self.assertEqual(week.delivery["send_on"], "2026-03-12")
        self.assertEqual(week.start_date, "2026-03-09")

        with self.assertRaises(ValueError):
            normalize_week_payload("2026-03-09", {"start_date": "2026-03-09", "end_date": "2026-03-08", "events": []})

        with self.assertRaises(ValueError):
            normalize_week_payload("2026-03-09", {"start_date": "2026-03-09", "end_date": "2026-03-15", "events": {}})

    def test_memory_store_lifecycle(self):
        store = MemoryWeeklyEmailStore()
        created = store.create_week_if_missing("2026-03-09", build_blank_week_payload("2026-03-09"))
        self.assertIsNotNone(created)
        self.assertIsNone(store.create_week_if_missing("2026-03-09", build_blank_week_payload("2026-03-09")))

        week = store.add_event("2026-03-09", self._sample_event())
        self.assertEqual(len(week.events), 1)
        self.assertEqual(week.events[0].source, "custom")

        store.save_week(
            "2026-03-09",
            {
                **week.to_dict(),
                "delivery": {"mode": "skip"},
            },
        )
        with self.assertRaises(ValueError):
            store.approve_week("2026-03-09")

        payload = store.get_week("2026-03-09").to_dict()
        payload["delivery"] = {"mode": "default", "send_on": "2026-03-08"}
        store.save_week("2026-03-09", payload)
        approved = store.approve_week("2026-03-09", approved_by="reviewer")
        claimed = store.claim_week_send("2026-03-09", sending_by="sender")
        sent = store.mark_week_sent("2026-03-09", sent_by="sender")
        reset = store.reset_week_send("2026-03-09")
        updated = store.update_week_metadata("2026-03-09", {"send": {"status": "reset"}})

        self.assertTrue(approved.approval["approved"])
        self.assertTrue(claimed.sent["sending"])
        self.assertTrue(sent.sent["sent"])
        self.assertFalse(reset.sent["sent"])
        self.assertEqual(updated.metadata["send"]["status"], "reset")

        with self.assertRaises(KeyError):
            store.approve_week("2026-03-16")

        store._weeks["2026-03-09"].sent = {
            "sent": True,
            "sent_at": "2026-03-10T00:00:00Z",
            "sent_by": "sender",
            "sending": False,
            "sending_at": "",
            "sending_by": "",
        }
        with self.assertRaises(ValueError):
            assert_week_editable(store._weeks["2026-03-09"])

    def test_firestore_store_create_save_and_transactional_updates(self):
        client = _FakeClient()
        store = FirestoreWeeklyEmailStore()
        store._client = client

        with patch.object(weekly_store_module, "firestore", _FakeFirestoreModule(client)):
            created = store.create_week_if_missing(
                "2026-03-09",
                {
                    **build_blank_week_payload("2026-03-09"),
                    "events": [
                        self._sample_event(id="event-1", title="First Event"),
                        self._sample_event(id="event-2", title="Second Event", start_date="2026-03-12", end_date="2026-03-12"),
                    ],
                },
            )
            self.assertIsNotNone(created)
            self.assertIsNone(store.create_week_if_missing("2026-03-09", build_blank_week_payload("2026-03-09")))

            saved = store.save_week(
                "2026-03-09",
                {
                    **build_blank_week_payload("2026-03-09"),
                    "events": [self._sample_event(id="event-1", title="Only Event")],
                },
            )
            self.assertEqual([event.id for event in saved.events], ["event-1"])

            added = store.add_event(
                "2026-03-09",
                self._sample_event(id="event-3", title="Added Event", start_date="2026-03-13", end_date="2026-03-13"),
            )
            self.assertEqual([event.id for event in added.events], ["event-1", "event-3"])

            approved = store.approve_week("2026-03-09", approved_by="reviewer")
            claimed = store.claim_week_send("2026-03-09", sending_by="sender")
            sent = store.mark_week_sent("2026-03-09", sent_by="sender")
            reset = store.reset_week_send("2026-03-09")
            updated = store.update_week_metadata("2026-03-09", {"automation": {"status": "ok"}})

            self.assertTrue(approved.approval["approved"])
            self.assertTrue(claimed.sent["sending"])
            self.assertTrue(sent.sent["sent"])
            self.assertFalse(reset.sent["sent"])
            self.assertEqual(updated.metadata["automation"]["status"], "ok")

    def test_firestore_store_transactional_errors_are_raised(self):
        client = _FakeClient()
        store = FirestoreWeeklyEmailStore()
        store._client = client

        with patch.object(weekly_store_module, "firestore", _FakeFirestoreModule(client)):
            with self.assertRaises(KeyError):
                store.approve_week("2026-03-09")

            store.create_week_if_missing("2026-03-09", build_blank_week_payload("2026-03-09"))
            with self.assertRaises(ValueError):
                store.claim_week_send("2026-03-09", sending_by="sender")

            approved = store.approve_week("2026-03-09", approved_by="reviewer")
            self.assertTrue(approved.approval["approved"])

            with self.assertRaises(ValueError):
                store.mark_week_sent("2026-03-09", sent_by="sender")

            claimed = store.claim_week_send("2026-03-09", sending_by="sender")
            self.assertTrue(claimed.sent["sending"])

            with self.assertRaises(ValueError):
                store.claim_week_send("2026-03-09", sending_by="sender")

    def test_firestore_store_get_client_supports_emulator_service_account_and_adc(self):
        fake_client = _FakeClient()
        fake_firebase_admin = _FakeFirebaseAdmin()
        fake_credentials = _FakeCredentials()
        fake_firestore = _FakeFirestoreModule(fake_client)

        with (
            patch.object(weekly_store_module, "firebase_admin", fake_firebase_admin),
            patch.object(weekly_store_module, "credentials", fake_credentials),
            patch.object(weekly_store_module, "firestore", fake_firestore),
        ):
            emulator_store = FirestoreWeeklyEmailStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="emailWeeks",
                    project_id="project-1",
                    emulator_host="localhost:8080",
                )
            )
            self.assertIs(emulator_store._get_client(), fake_client)
            self.assertEqual(fake_firebase_admin.init_calls[-1]["options"], {"projectId": "project-1"})

            fake_firebase_admin._apps = []
            service_account_store = FirestoreWeeklyEmailStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="emailWeeks",
                    project_id="project-1",
                    service_account_json='{"type":"service_account"}',
                )
            )
            service_account_store._get_client()
            self.assertEqual(fake_credentials.certificate_payloads[-1], {"type": "service_account"})

            fake_firebase_admin._apps = []
            adc_store = FirestoreWeeklyEmailStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="emailWeeks",
                    project_id="project-1",
                )
            )
            adc_store._get_client()
            self.assertEqual(fake_credentials.default_calls, 1)

        with (
            patch.object(weekly_store_module, "firebase_admin", None),
            patch.object(weekly_store_module, "firestore", None),
        ):
            with self.assertRaises(RuntimeError):
                FirestoreWeeklyEmailStore()._get_client()


if __name__ == "__main__":
    unittest.main()
