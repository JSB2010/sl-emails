import unittest

from sl_emails.services.admin_settings import (
    EmailAdminSettings,
    FirestoreAdminSettingsStore,
    MemoryAdminSettingsStore,
    build_automation_settings_payload,
    normalize_email_list,
    normalize_sender_metadata,
    validate_sender_metadata,
)


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

    def set(self, payload):
        self._store[self._document_id] = dict(payload)


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(self._store, document_id)


class _FakeFirestoreClient:
    def __init__(self):
        self.documents = {}

    def collection(self, _name):
        return _FakeCollection(self.documents)


class _FakeWeeklyStore:
    def __init__(self, client):
        self._client = client

    def _get_client(self):
        return self._client


class AdminSettingsTests(unittest.TestCase):
    def test_normalize_email_list_splits_dedupes_and_normalizes(self):
        emails = normalize_email_list(" AppDev@KentDenver.org; ops@kentdenver.org,appdev@kentdenver.org ")

        self.assertEqual(emails, ["appdev@kentdenver.org", "ops@kentdenver.org"])

    def test_normalize_email_list_rejects_invalid_email(self):
        with self.assertRaises(ValueError):
            normalize_email_list(["appdev@kentdenver.org", "not-an-email"])

    def test_normalize_sender_metadata_applies_defaults_and_normalizes_recipients(self):
        metadata = normalize_sender_metadata(
            {
                "email_from_name": "  KD Student Leadership  ",
                "reply_to_email": " StudentLeader@KentDenver.org ",
                "audience_recipients": {
                    "middle_school": {
                        "to": " Middle@KentDenver.org ",
                        "bcc": "one@kentdenver.org; two@kentdenver.org",
                    },
                    "upper_school": {
                        "to": "Upper@KentDenver.org",
                        "bcc": ["upperbcc@kentdenver.org"],
                    },
                },
            }
        )

        self.assertEqual(metadata["email_from_name"], "KD Student Leadership")
        self.assertEqual(metadata["reply_to_email"], "studentleader@kentdenver.org")
        self.assertEqual(metadata["timezone"], "America/Denver")
        self.assertEqual(metadata["audience_recipients"]["middle_school"]["to"], "middle@kentdenver.org")
        self.assertEqual(
            metadata["audience_recipients"]["middle_school"]["bcc"],
            ["one@kentdenver.org", "two@kentdenver.org"],
        )
        self.assertEqual(metadata["audience_recipients"]["upper_school"]["to"], "upper@kentdenver.org")

    def test_normalize_sender_metadata_rejects_invalid_recipient_and_reply_to(self):
        with self.assertRaises(ValueError):
            normalize_sender_metadata(
                {
                    "audience_recipients": {
                        "middle_school": {"to": "not-an-email", "bcc": []},
                        "upper_school": {"to": "upper@kentdenver.org", "bcc": []},
                    }
                }
            )

        with self.assertRaises(ValueError):
            normalize_sender_metadata(
                {
                    "reply_to_email": "not-an-email",
                    "audience_recipients": {
                        "middle_school": {"to": "middle@kentdenver.org", "bcc": []},
                        "upper_school": {"to": "upper@kentdenver.org", "bcc": []},
                    },
                }
            )

    def test_validate_sender_metadata_requires_to_recipients_for_both_audiences(self):
        with self.assertRaises(ValueError):
            validate_sender_metadata(
                {
                    "audience_recipients": {
                        "middle_school": {"to": "", "bcc": []},
                        "upper_school": {"to": "upper@kentdenver.org", "bcc": []},
                    }
                }
            )

        with self.assertRaises(ValueError):
            validate_sender_metadata(
                {
                    "audience_recipients": {
                        "middle_school": {"to": "middle@kentdenver.org", "bcc": []},
                        "upper_school": {"to": "", "bcc": []},
                    }
                }
            )

    def test_build_automation_settings_payload_uses_normalized_sender_metadata(self):
        settings = EmailAdminSettings(
            allowed_admin_emails=["appdev@kentdenver.org"],
            ops_notification_emails=["ops@kentdenver.org"],
            sender_metadata={
                "email_from_name": "KD Athletics",
                "reply_to_email": "reply@kentdenver.org",
                "timezone": "America/Denver",
                "audience_recipients": {
                    "middle_school": {"to": "middle@kentdenver.org", "bcc": ["middlebcc@kentdenver.org"]},
                    "upper_school": {"to": "upper@kentdenver.org", "bcc": ["upperbcc@kentdenver.org"]},
                },
            },
        )

        payload = build_automation_settings_payload(settings)

        self.assertEqual(payload["admin_notification_emails"], ["ops@kentdenver.org"])
        self.assertEqual(payload["email_from_name"], "KD Athletics")
        self.assertEqual(payload["reply_to_email"], "reply@kentdenver.org")
        self.assertEqual(payload["email_recipients"]["middle_school"]["to"], "middle@kentdenver.org")

    def test_memory_store_get_settings_returns_none_until_bootstrapped(self):
        store = MemoryAdminSettingsStore()

        self.assertIsNone(store.get_settings())

    def test_memory_store_rejects_empty_admin_or_notification_lists(self):
        store = MemoryAdminSettingsStore()

        with self.assertRaises(ValueError):
            store.ensure_settings(
                allowed_admin_emails=[],
                ops_notification_emails=["ops@kentdenver.org"],
                actor="bootstrap",
            )

        with self.assertRaises(ValueError):
            store.ensure_settings(
                allowed_admin_emails=["appdev@kentdenver.org"],
                ops_notification_emails=[],
                actor="bootstrap",
            )

    def test_memory_store_bootstraps_and_preserves_created_fields_on_update(self):
        store = MemoryAdminSettingsStore()

        created = store.ensure_settings(
            allowed_admin_emails=["appdev@kentdenver.org"],
            ops_notification_emails=["ops@kentdenver.org"],
            actor="bootstrap",
        )
        updated = store.update_settings(
            allowed_admin_emails=["appdev@kentdenver.org", "newadmin@kentdenver.org"],
            ops_notification_emails=["ops@kentdenver.org", "another@kentdenver.org"],
            sender_metadata={
                "email_from_name": "KD Student Leadership",
                "reply_to_email": "studentleader@kentdenver.org",
                "timezone": "America/Denver",
                "audience_recipients": {
                    "middle_school": {"to": "middle@kentdenver.org", "bcc": []},
                    "upper_school": {"to": "upper@kentdenver.org", "bcc": []},
                },
            },
            actor="admin-user",
        )

        self.assertEqual(created.created_by, "bootstrap")
        self.assertEqual(updated.created_at, created.created_at)
        self.assertEqual(updated.created_by, "bootstrap")
        self.assertEqual(updated.updated_by, "admin-user")
        self.assertIn("newadmin@kentdenver.org", updated.allowed_admin_emails)
        self.assertEqual(
            updated.sender_metadata["audience_recipients"]["middle_school"]["to"],
            "middle@kentdenver.org",
        )

    def test_firestore_store_can_ensure_and_update_settings(self):
        client = _FakeFirestoreClient()
        store = FirestoreAdminSettingsStore()
        store._weekly_store = _FakeWeeklyStore(client)

        self.assertIsNone(store.get_settings())

        ensured = store.ensure_settings(
            allowed_admin_emails=["appdev@kentdenver.org"],
            ops_notification_emails=["ops@kentdenver.org"],
            actor="bootstrap",
        )
        updated = store.update_settings(
            allowed_admin_emails=["appdev@kentdenver.org", "newadmin@kentdenver.org"],
            ops_notification_emails=["ops@kentdenver.org", "another@kentdenver.org"],
            sender_metadata={
                "email_from_name": "KD Student Leadership",
                "reply_to_email": "studentleader@kentdenver.org",
                "timezone": "America/Denver",
                "audience_recipients": {
                    "middle_school": {"to": "middle@kentdenver.org", "bcc": []},
                    "upper_school": {"to": "upper@kentdenver.org", "bcc": []},
                },
            },
            actor="admin-user",
        )

        self.assertEqual(ensured.allowed_admin_emails, ["appdev@kentdenver.org"])
        self.assertIn("newadmin@kentdenver.org", updated.allowed_admin_emails)
        self.assertEqual(updated.updated_by, "admin-user")
        self.assertIn(store.document_id, client.documents)
        self.assertEqual(
            client.documents[store.document_id]["sender_metadata"]["audience_recipients"]["upper_school"]["to"],
            "upper@kentdenver.org",
        )


if __name__ == "__main__":
    unittest.main()
