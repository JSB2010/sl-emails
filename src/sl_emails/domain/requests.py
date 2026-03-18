from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any
from uuid import uuid4

from .dates import iso_to_date
from .weekly import AUDIENCES, normalize_audiences


def week_start_for_date(value: str) -> str:
    day = iso_to_date(value)
    return (day - timedelta(days=day.weekday())).isoformat()


def default_request_review() -> dict[str, Any]:
    return {
        "decision": "",
        "reviewed_at": "",
        "reviewed_by": "",
        "reviewer_notes": "",
        "resolved_event_id": "",
    }


def normalize_request_review(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return default_request_review()
    return {
        "decision": str(payload.get("decision") or "").strip().lower(),
        "reviewed_at": str(payload.get("reviewed_at") or "").strip(),
        "reviewed_by": str(payload.get("reviewed_by") or "").strip(),
        "reviewer_notes": str(payload.get("reviewer_notes") or "").strip(),
        "resolved_event_id": str(payload.get("resolved_event_id") or "").strip(),
    }


@dataclass
class EventRequestRecord:
    request_id: str
    week_id: str
    title: str
    start_date: str
    end_date: str
    time_text: str
    location: str
    category: str
    audiences: list[str]
    requester_name: str
    requester_email: str
    kind: str = "event"
    subtitle: str = ""
    description: str = ""
    link: str = ""
    requester_notes: str = ""
    team: str = ""
    opponent: str = ""
    is_home: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    review: dict[str, Any] = field(default_factory=default_request_review)
    submitted_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_firestore(self) -> dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EventRequestRecord":
        data = dict(payload)
        start_date = str(data.get("start_date") or data.get("date") or "").strip()
        title = str(data.get("title") or data.get("team") or "Untitled Request").strip() or "Untitled Request"
        return cls(
            request_id=str(data.get("request_id") or data.get("id") or "").strip() or uuid4().hex,
            week_id=str(data.get("week_id") or week_start_for_date(start_date)).strip() if start_date else "",
            title=title,
            start_date=start_date,
            end_date=str(data.get("end_date") or start_date).strip(),
            time_text=str(data.get("time_text") or data.get("time") or "TBA").strip() or "TBA",
            location=str(data.get("location") or "On Campus").strip() or "On Campus",
            category=str(data.get("category") or "School Event").strip() or "School Event",
            audiences=normalize_audiences(data.get("audiences")) or list(AUDIENCES),
            requester_name=str(data.get("requester_name") or "").strip(),
            requester_email=str(data.get("requester_email") or "").strip().lower(),
            kind=str(data.get("kind") or "event").strip().lower() or "event",
            subtitle=str(data.get("subtitle") or "").strip(),
            description=str(data.get("description") or "").strip(),
            link=str(data.get("link") or "").strip(),
            requester_notes=str(data.get("requester_notes") or data.get("notes") or "").strip(),
            team=str(data.get("team") or title).strip(),
            opponent=str(data.get("opponent") or "").strip(),
            is_home=bool(data.get("is_home", True)),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
            status=str(data.get("status") or "pending").strip().lower() or "pending",
            review=normalize_request_review(data.get("review")),
            submitted_at=str(data.get("submitted_at") or "").strip(),
            updated_at=str(data.get("updated_at") or "").strip(),
        )


__all__ = [
    "EventRequestRecord",
    "default_request_review",
    "normalize_request_review",
    "week_start_for_date",
]
