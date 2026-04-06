import unittest
from unittest.mock import patch

from sl_emails.config import RuntimeFirestoreConfig
from sl_emails.services import signage_store as signage_store_module
from sl_emails.services.signage_store import FirestoreSignageStore


class _FakeSnapshot:
    def __init__(self, payload):
        self._payload = payload
        self.exists = payload is not None

    def to_dict(self):
        return dict(self._payload) if isinstance(self._payload, dict) else {}


class _FakeDocumentRef:
    def __init__(self, store, document_id):
        self._store = store
        self._document_id = document_id

    def get(self):
        return _FakeSnapshot(self._store.get(self._document_id))

    def set(self, payload, merge=False):
        if merge and self._document_id in self._store:
            merged = dict(self._store[self._document_id])
            merged.update(payload)
            self._store[self._document_id] = merged
        else:
            self._store[self._document_id] = dict(payload)


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(self._store, document_id)


class _FakeClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return _FakeCollection(self.collections.setdefault(name, {}))


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


class FirestoreSignageStoreInitTests(unittest.TestCase):
    def test_get_client_supports_emulator_service_account_and_adc(self):
        fake_client = _FakeClient()
        fake_firebase_admin = _FakeFirebaseAdmin()
        fake_credentials = _FakeCredentials()
        fake_firestore = _FakeFirestoreModule(fake_client)

        with (
            patch.object(signage_store_module, "firebase_admin", fake_firebase_admin),
            patch.object(signage_store_module, "credentials", fake_credentials),
            patch.object(signage_store_module, "firestore", fake_firestore),
        ):
            emulator_store = FirestoreSignageStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="signageDays",
                    project_id="project-1",
                    emulator_host="localhost:8080",
                )
            )
            self.assertIs(emulator_store._get_client(), fake_client)
            self.assertEqual(fake_firebase_admin.init_calls[-1]["options"], {"projectId": "project-1"})

            fake_firebase_admin._apps = []
            service_account_store = FirestoreSignageStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="signageDays",
                    project_id="project-1",
                    service_account_json='{"type":"service_account"}',
                )
            )
            service_account_store._get_client()
            self.assertEqual(fake_credentials.certificate_payloads[-1], {"type": "service_account"})

            fake_firebase_admin._apps = []
            adc_store = FirestoreSignageStore(
                runtime_config=RuntimeFirestoreConfig(
                    collection_name="signageDays",
                    project_id="project-1",
                )
            )
            adc_store._get_client()
            self.assertEqual(fake_credentials.default_calls, 1)

        with (
            patch.object(signage_store_module, "firebase_admin", None),
            patch.object(signage_store_module, "firestore", None),
        ):
            with self.assertRaises(RuntimeError):
                FirestoreSignageStore()._get_client()

    def test_update_day_metadata_merges_and_missing_days_raise(self):
        client = _FakeClient()
        store = FirestoreSignageStore(collection_name="signageDays")
        store._client = client

        day_ref = client.collection("signageDays").document("2026-03-23")
        day_ref.set(
            {
                "date": "2026-03-23",
                "events": [],
                "source_summary": {"athletics_events": 0, "arts_events": 0, "total_events": 0},
                "metadata": {"ingest": {"status": "success", "actor": "system"}},
            }
        )

        updated = store.update_day_metadata("2026-03-23", {"ingest": {"message": "ok"}})

        self.assertEqual(updated.metadata["ingest"]["status"], "success")
        self.assertEqual(updated.metadata["ingest"]["message"], "ok")

        with self.assertRaises(KeyError):
            store.update_day_metadata("2026-03-24", {"ingest": {"status": "failed"}})

    def test_save_day_persists_and_reads_back(self):
        client = _FakeClient()
        store = FirestoreSignageStore(collection_name="signageDays")
        store._client = client

        saved = store.save_day(
            "2026-03-25",
            {
                "events": [{"title": "Spring Concert", "date": "2026-03-25"}],
                "source_summary": {"athletics_events": 0, "arts_events": 1, "total_events": 1},
                "metadata": {"ingest": {"status": "success"}},
            },
        )

        self.assertEqual(saved.day_id, "2026-03-25")
        self.assertEqual(saved.source_summary["arts_events"], 1)
        self.assertEqual(store.get_day("2026-03-25").events[0].title, "Spring Concert")


if __name__ == "__main__":
    unittest.main()
