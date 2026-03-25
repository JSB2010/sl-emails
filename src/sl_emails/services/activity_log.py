from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from sl_emails.config import EMAILS_ACTIVITY_COLLECTION
from sl_emails.domain.dates import utc_now_iso
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore


@dataclass
class EmailActivityRecord:
    event_type: str
    status: str
    actor: str
    week_id: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = ""
    activity_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload["occurred_at"]:
            payload["occurred_at"] = utc_now_iso()
        if not payload["activity_id"]:
            payload["activity_id"] = uuid4().hex
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EmailActivityRecord":
        data = dict(payload or {})
        return cls(
            event_type=str(data.get("event_type") or "").strip(),
            status=str(data.get("status") or "").strip(),
            actor=str(data.get("actor") or "").strip(),
            week_id=str(data.get("week_id") or "").strip(),
            message=str(data.get("message") or "").strip(),
            details=data.get("details") if isinstance(data.get("details"), dict) else {},
            occurred_at=str(data.get("occurred_at") or "").strip(),
            activity_id=str(data.get("activity_id") or "").strip(),
        )


class ActivityLogStore(Protocol):
    def log(
        self,
        *,
        event_type: str,
        status: str,
        actor: str,
        week_id: str = "",
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> EmailActivityRecord: ...

    def list_recent(self, *, week_id: str = "", limit: int = 20) -> list[EmailActivityRecord]: ...


class MemoryActivityLogStore:
    def __init__(self) -> None:
        self.records: list[EmailActivityRecord] = []

    def log(
        self,
        *,
        event_type: str,
        status: str,
        actor: str,
        week_id: str = "",
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> EmailActivityRecord:
        record = EmailActivityRecord(
            event_type=event_type,
            status=status,
            actor=actor,
            week_id=week_id,
            message=message,
            details=details or {},
            occurred_at=utc_now_iso(),
            activity_id=uuid4().hex,
        )
        self.records.append(record)
        return record

    def list_recent(self, *, week_id: str = "", limit: int = 20) -> list[EmailActivityRecord]:
        items = [
            EmailActivityRecord.from_dict(record.to_dict())
            for record in self.records
            if not week_id or record.week_id == week_id
        ]
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[: max(0, limit)]


class FirestoreActivityLogStore:
    def __init__(self, *, collection_name: str = EMAILS_ACTIVITY_COLLECTION) -> None:
        self.collection_name = collection_name
        self._weekly_store = FirestoreWeeklyEmailStore()

    def log(
        self,
        *,
        event_type: str,
        status: str,
        actor: str,
        week_id: str = "",
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> EmailActivityRecord:
        record = EmailActivityRecord(
            event_type=event_type,
            status=status,
            actor=actor,
            week_id=week_id,
            message=message,
            details=details or {},
            occurred_at=utc_now_iso(),
            activity_id=uuid4().hex,
        )
        self._weekly_store._get_client().collection(self.collection_name).document(record.activity_id).set(record.to_dict())
        return record

    def list_recent(self, *, week_id: str = "", limit: int = 20) -> list[EmailActivityRecord]:
        snapshots = self._weekly_store._get_client().collection(self.collection_name).stream()
        items = [
            EmailActivityRecord.from_dict(snapshot.to_dict() or {})
            for snapshot in snapshots
        ]
        if week_id:
            items = [item for item in items if item.week_id == week_id]
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[: max(0, limit)]


__all__ = [
    "ActivityLogStore",
    "EmailActivityRecord",
    "FirestoreActivityLogStore",
    "MemoryActivityLogStore",
]
