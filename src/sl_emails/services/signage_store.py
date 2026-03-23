from __future__ import annotations

from typing import Any, Protocol
import json

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    credentials = None
    firestore = None

from ..config import RuntimeFirestoreConfig
from ..domain.dates import utc_now_iso
from ..domain.signage import SignageDayRecord


SIGNAGE_DAYS_COLLECTION = "signageDays"


class SignageStore(Protocol):
    def get_day(self, day_id: str) -> SignageDayRecord | None: ...

    def save_day(self, day_id: str, payload: dict[str, Any]) -> SignageDayRecord: ...


def normalize_signage_day_payload(
    day_id: str,
    payload: dict[str, Any],
    *,
    existing: SignageDayRecord | None = None,
) -> SignageDayRecord:
    timestamp = utc_now_iso()
    normalized = SignageDayRecord.from_dict(
        {
            "date": day_id,
            "events": payload.get("events") if isinstance(payload.get("events"), list) else (existing.to_dict().get("events", []) if existing else []),
            "source_summary": payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else (dict(existing.source_summary) if existing else {}),
            "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else (dict(existing.metadata) if existing else {}),
            "created_at": existing.created_at if existing else timestamp,
            "updated_at": timestamp,
        }
    )
    normalized.day_id = day_id
    if not normalized.created_at:
        normalized.created_at = timestamp
    if not normalized.updated_at:
        normalized.updated_at = timestamp
    return normalized


class MemorySignageStore:
    def __init__(self) -> None:
        self._days: dict[str, SignageDayRecord] = {}

    def get_day(self, day_id: str) -> SignageDayRecord | None:
        day = self._days.get(day_id)
        if day is None:
            return None
        return SignageDayRecord.from_dict(day.to_dict())

    def save_day(self, day_id: str, payload: dict[str, Any]) -> SignageDayRecord:
        existing = self._days.get(day_id)
        day = normalize_signage_day_payload(day_id, payload, existing=existing)
        self._days[day_id] = day
        return self.get_day(day_id)  # type: ignore[return-value]


class FirestoreSignageStore:
    def __init__(
        self,
        *,
        collection_name: str | None = None,
        project_id: str | None = None,
        runtime_config: RuntimeFirestoreConfig | None = None,
    ) -> None:
        self.runtime_config = runtime_config or RuntimeFirestoreConfig.from_env(
            collection_name=collection_name or SIGNAGE_DAYS_COLLECTION,
            project_id=project_id,
        )
        self.collection_name = self.runtime_config.collection_name or SIGNAGE_DAYS_COLLECTION
        self.project_id = self.runtime_config.project_id
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if firebase_admin is None or firestore is None:
            raise RuntimeError("firebase_admin is not available. Install Firebase Admin SDK to use Firestore storage.")
        if not firebase_admin._apps:
            options = {"projectId": self.project_id} if self.project_id else None
            service_account_json = self.runtime_config.service_account_json
            if self.runtime_config.emulator_host and not service_account_json:
                firebase_admin.initialize_app(options=options)
            elif service_account_json:
                credential = credentials.Certificate(json.loads(service_account_json))
                firebase_admin.initialize_app(credential=credential, options=options)
            else:
                credential = credentials.ApplicationDefault()
                firebase_admin.initialize_app(credential=credential, options=options)
        self._client = firestore.client()
        return self._client

    def _day_ref(self, day_id: str):
        return self._get_client().collection(self.collection_name).document(day_id)

    def get_day(self, day_id: str) -> SignageDayRecord | None:
        snapshot = self._day_ref(day_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        payload.setdefault("date", day_id)
        return SignageDayRecord.from_dict(payload)

    def save_day(self, day_id: str, payload: dict[str, Any]) -> SignageDayRecord:
        existing = self.get_day(day_id)
        day = normalize_signage_day_payload(day_id, payload, existing=existing)
        self._day_ref(day_id).set(day.to_dict())
        return self.get_day(day_id)  # type: ignore[return-value]
