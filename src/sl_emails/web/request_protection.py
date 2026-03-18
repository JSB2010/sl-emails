from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from hashlib import sha256
from time import time
from typing import Any
from urllib.parse import urlparse


HONEYPOT_FIELD = "website"


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


def first_forwarded_ip(raw_forwarded_for: str, remote_addr: str) -> str:
    forwarded = [part.strip() for part in str(raw_forwarded_for or "").split(",") if part.strip()]
    return forwarded[0] if forwarded else str(remote_addr or "").strip()

