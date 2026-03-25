import unittest
from unittest.mock import patch

from sl_emails.web.request_protection import FirestoreRequestProtector, RequestRateLimitExceeded


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


class _FakeWeeklyStore:
    def __init__(self, client):
        self._client = client

    def _get_client(self):
        return self._client


class FirestoreRequestProtectorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
