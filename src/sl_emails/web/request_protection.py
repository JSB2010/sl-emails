from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from hashlib import sha256
from time import time
from typing import Any
from urllib.parse import urlparse

try:
    from firebase_admin import firestore
except ImportError:  # pragma: no cover
    firestore = None

from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore


HONEYPOT_FIELD = "website"
REQUEST_RATE_LIMITS_COLLECTION = "emailRequestRateLimits"


class RequestProtectionError(ValueError):
    status_code = 400


class RequestRateLimitExceeded(RequestProtectionError):
    status_code = 429


@dataclass
class PublicRequestProtector:
    max_attempts: int = 5
    window_seconds: int = 15 * 60
    _attempts: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._attempts[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        return bucket

    def check_rate_limit(self, fingerprint: str) -> None:
        now = time()
        bucket = self._prune(fingerprint, now)
        if len(bucket) >= self.max_attempts:
            raise RequestRateLimitExceeded("Too many request submissions from this source. Please wait and try again later.")
        bucket.append(now)

    def validate_honeypot(self, payload: dict[str, Any]) -> None:
        if str(payload.get(HONEYPOT_FIELD) or "").strip():
            raise RequestProtectionError("Request could not be accepted.")

    def submission_metadata(self, *, remote_addr: str, user_agent: str, referrer: str) -> dict[str, str]:
        parsed_referrer = urlparse(referrer) if referrer else None
        return {
            "ip_hash": sha256(remote_addr.encode("utf-8")).hexdigest()[:16] if remote_addr else "",
            "user_agent_hash": sha256(user_agent.encode("utf-8")).hexdigest()[:16] if user_agent else "",
            "referrer_host": (parsed_referrer.netloc or "").lower() if parsed_referrer else "",
        }


@dataclass
class FirestoreRequestProtector(PublicRequestProtector):
    bucket_seconds: int = 60
    collection_name: str = REQUEST_RATE_LIMITS_COLLECTION
    _weekly_store: FirestoreWeeklyEmailStore = field(default_factory=FirestoreWeeklyEmailStore)

    def _fingerprint_hash(self, fingerprint: str) -> str:
        return sha256(str(fingerprint or "").encode("utf-8")).hexdigest()

    def _bucket_start(self, now: float) -> int:
        return int(now // self.bucket_seconds) * self.bucket_seconds

    def _bucket_starts(self, now: float) -> list[int]:
        current_start = self._bucket_start(now)
        first_start = self._bucket_start(max(0.0, now - self.window_seconds + 1))
        return list(range(first_start, current_start + self.bucket_seconds, self.bucket_seconds))

    def _collection(self):
        return self._weekly_store._get_client().collection(self.collection_name)

    def _bucket_ref(self, fingerprint_hash: str, bucket_start: int):
        return self._collection().document(f"{fingerprint_hash}:{bucket_start}")

    def _bucket_payload(self, *, fingerprint_hash: str, bucket_start: int, count: int) -> dict[str, Any]:
        return {
            "fingerprint_hash": fingerprint_hash,
            "bucket_start": bucket_start,
            "count": count,
            "expires_at": float(bucket_start + self.window_seconds + self.bucket_seconds),
            "updated_at": float(time()),
        }

    def _prune_expired(self, now: float) -> None:
        try:
            query = self._collection().where("expires_at", "<", float(now)).limit(20)
            snapshots = list(query.stream())
        except Exception:
            return
        for snapshot in snapshots:
            try:
                snapshot.reference.delete()
            except Exception:
                continue

    def _enforce_limit_without_transaction(self, fingerprint_hash: str, now: float) -> None:
        bucket_starts = self._bucket_starts(now)
        current_start = bucket_starts[-1]
        total = 0
        current_count = 0
        for bucket_start in bucket_starts:
            snapshot = self._bucket_ref(fingerprint_hash, bucket_start).get()
            payload = snapshot.to_dict() if snapshot.exists else {}
            if float(payload.get("expires_at", 0) or 0) <= now:
                payload = {}
            count = int(payload.get("count", 0) or 0)
            total += count
            if bucket_start == current_start:
                current_count = count
        if total >= self.max_attempts:
            raise RequestRateLimitExceeded("Too many request submissions from this source. Please wait and try again later.")
        self._bucket_ref(fingerprint_hash, current_start).set(
            self._bucket_payload(
                fingerprint_hash=fingerprint_hash,
                bucket_start=current_start,
                count=current_count + 1,
            ),
            merge=True,
        )

    def check_rate_limit(self, fingerprint: str) -> None:
        fingerprint_hash = self._fingerprint_hash(fingerprint)
        now = time()
        bucket_starts = self._bucket_starts(now)
        current_start = bucket_starts[-1]
        client = self._weekly_store._get_client()

        if firestore is None or not hasattr(client, "transaction"):
            self._enforce_limit_without_transaction(fingerprint_hash, now)
            self._prune_expired(now)
            return

        transaction = client.transaction()

        @firestore.transactional
        def apply(transaction: Any) -> None:
            total = 0
            current_count = 0
            for bucket_start in bucket_starts:
                ref = self._bucket_ref(fingerprint_hash, bucket_start)
                snapshot = ref.get(transaction=transaction)
                payload = snapshot.to_dict() if snapshot.exists else {}
                if float(payload.get("expires_at", 0) or 0) <= now:
                    payload = {}
                count = int(payload.get("count", 0) or 0)
                total += count
                if bucket_start == current_start:
                    current_count = count
            if total >= self.max_attempts:
                raise RequestRateLimitExceeded("Too many request submissions from this source. Please wait and try again later.")
            transaction.set(
                self._bucket_ref(fingerprint_hash, current_start),
                self._bucket_payload(
                    fingerprint_hash=fingerprint_hash,
                    bucket_start=current_start,
                    count=current_count + 1,
                ),
                merge=True,
            )

        apply(transaction)
        self._prune_expired(now)


def first_forwarded_ip(raw_forwarded_for: str, remote_addr: str) -> str:
    forwarded = [part.strip() for part in str(raw_forwarded_for or "").split(",") if part.strip()]
    return forwarded[0] if forwarded else str(remote_addr or "").strip()
