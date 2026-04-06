import unittest
from unittest.mock import patch

from sl_emails.web.request_protection import (
    FirestoreRequestProtector,
    PublicRequestProtector,
    RequestProtectionError,
    RequestRateLimitExceeded,
    first_forwarded_ip,
)


class _FakeSnapshot:
    def __init__(self, document_id, store):
        self._document_id = document_id
        self._store = store
        self.reference = _FakeDocumentRef(document_id, store)

    @property
    def exists(self):
        return self._document_id in self._store

    def to_dict(self):
        return dict(self._store.get(self._document_id, {}))


class _FakeDocumentRef:
    def __init__(self, document_id, store):
        self._document_id = document_id
        self._store = store

    def get(self, transaction=None):
        return _FakeSnapshot(self._document_id, self._store)

    def set(self, payload, merge=False):
        if merge and self._document_id in self._store:
            merged = dict(self._store[self._document_id])
            merged.update(payload)
            self._store[self._document_id] = merged
        else:
            self._store[self._document_id] = dict(payload)

    def delete(self):
        self._store.pop(self._document_id, None)


class _FakeQuery:
    def __init__(self, store, field, op, value):
        self._store = store
        self._field = field
        self._op = op
        self._value = value
        self._limit = None

    def limit(self, value):
        self._limit = value
        return self

    def stream(self):
        items = []
        for document_id, payload in self._store.items():
            candidate = payload.get(self._field)
            if self._op == "<" and candidate is not None and candidate < self._value:
                items.append(_FakeSnapshot(document_id, self._store))
        if self._limit is not None:
            items = items[: self._limit]
        return items


class _FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, document_id):
        return _FakeDocumentRef(document_id, self._store)

    def where(self, field, op, value):
        return _FakeQuery(self._store, field, op, value)


class _FakeFirestoreClient:
    def __init__(self):
        self.documents = {}

    def collection(self, name):
        return _FakeCollection(self.documents)


class _TransactionalClient(_FakeFirestoreClient):
    def transaction(self):
        return _FakeTransaction()


class _FakeTransaction:
    def set(self, ref, payload, merge=False):
        ref.set(payload, merge=merge)


class _FakeWeeklyStore:
    def __init__(self, client):
        self._client = client

    def _get_client(self):
        return self._client


class FirestoreRequestProtectorTests(unittest.TestCase):
    def test_public_request_protector_metadata_and_honeypot(self):
        protector = PublicRequestProtector()

        metadata = protector.submission_metadata(
            remote_addr="203.0.113.10",
            user_agent="Mozilla/5.0",
            referrer="https://example.test/request?foo=1",
        )

        self.assertEqual(metadata["referrer_host"], "example.test")
        self.assertTrue(metadata["ip_hash"])
        self.assertTrue(metadata["user_agent_hash"])

        with self.assertRaises(RequestProtectionError):
            protector.validate_honeypot({"website": "https://spam.example.test"})

    @patch("sl_emails.web.request_protection.time", return_value=1_710_000_000.0)
    def test_rate_limit_is_shared_across_instances(self, _mock_time):
        client = _FakeFirestoreClient()
        shared_store = _FakeWeeklyStore(client)
        protector_one = FirestoreRequestProtector(max_attempts=2, window_seconds=900, _weekly_store=shared_store)
        protector_two = FirestoreRequestProtector(max_attempts=2, window_seconds=900, _weekly_store=shared_store)

        protector_one.check_rate_limit("203.0.113.10|browser")
        protector_two.check_rate_limit("203.0.113.10|browser")

        with self.assertRaises(RequestRateLimitExceeded):
            protector_one.check_rate_limit("203.0.113.10|browser")

    @patch("sl_emails.web.request_protection.time", return_value=1_710_000_000.0)
    def test_transactional_rate_limit_path_is_enforced(self, _mock_time):
        client = _TransactionalClient()
        shared_store = _FakeWeeklyStore(client)
        protector = FirestoreRequestProtector(max_attempts=2, window_seconds=900, _weekly_store=shared_store)

        class _FakeFirestoreModule:
            @staticmethod
            def transactional(fn):
                return fn

        with patch("sl_emails.web.request_protection.firestore", _FakeFirestoreModule):
            protector.check_rate_limit("203.0.113.10|browser")
            protector.check_rate_limit("203.0.113.10|browser")
            with self.assertRaises(RequestRateLimitExceeded):
                protector.check_rate_limit("203.0.113.10|browser")

    def test_prune_expired_swallows_query_and_delete_failures(self):
        protector = FirestoreRequestProtector(_weekly_store=_FakeWeeklyStore(_FakeFirestoreClient()))

        with patch.object(protector, "_collection", side_effect=RuntimeError("query failed")):
            protector._prune_expired(1_710_000_000.0)

        class _BadRef:
            def delete(self):
                raise RuntimeError("delete failed")

        class _BadSnapshot:
            reference = _BadRef()

        class _BadQuery:
            def limit(self, _value):
                return self

            def stream(self):
                return [_BadSnapshot()]

        class _BadCollection:
            def where(self, *_args):
                return _BadQuery()

        with patch.object(protector, "_collection", return_value=_BadCollection()):
            protector._prune_expired(1_710_000_000.0)

    @patch("sl_emails.web.request_protection.time", return_value=1_710_000_000.0)
    def test_first_forwarded_ip_prefers_forwarded_header(self, _mock_time):
        self.assertEqual(first_forwarded_ip("198.51.100.2, 203.0.113.10", "127.0.0.1"), "198.51.100.2")
        self.assertEqual(first_forwarded_ip("", "127.0.0.1"), "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
