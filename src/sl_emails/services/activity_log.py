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


__all__ = [
    "ActivityLogStore",
    "EmailActivityRecord",
    "FirestoreActivityLogStore",
    "MemoryActivityLogStore",
]
