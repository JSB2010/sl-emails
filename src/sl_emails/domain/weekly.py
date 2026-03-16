from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from .styling import SOURCE_ACCENTS


AUDIENCES = ("middle-school", "upper-school")
DEFAULT_HEADING = "This Week at Kent Denver"
DEFAULT_STATUS = "draft"


def default_approval_state() -> dict[str, Any]:
    return {"approved": False, "approved_at": "", "approved_by": ""}


def default_sent_state(*, include_sending: bool = True) -> dict[str, Any]:
    state: dict[str, Any] = {"sent": False, "sent_at": "", "sent_by": ""}
    if include_sending:
        state.update({"sending": False, "sending_at": "", "sending_by": ""})
    return state


def normalize_sent_state(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return default_sent_state()
    return {
        "sent": bool(payload.get("sent", False)),
        "sent_at": str(payload.get("sent_at") or ""),
        "sent_by": str(payload.get("sent_by") or ""),
        "sending": bool(payload.get("sending", False)),
        "sending_at": str(payload.get("sending_at") or ""),
        "sending_by": str(payload.get("sending_by") or ""),
    }


def normalize_audiences(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip().lower().replace("_", "-")
        if value in {"all", "both"}:
            return list(AUDIENCES)
        if value in {"middle", "middle-school", "middle school", "ms"}:
            canonical = "middle-school"
        elif value in {"upper", "upper-school", "upper school", "us"}:
            canonical = "upper-school"
        else:
            continue
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
    return normalized


def looks_middle_school(label: str) -> bool:
    value = label.lower()
    indicators = ["middle school", " ms ", " 6th", " 7th", " 8th", "sixth", "seventh", "eighth"]
    padded = f" {value} "
    return any(indicator in padded for indicator in indicators)


def infer_audiences(payload: dict[str, Any], *, source: str) -> list[str]:
    explicit = normalize_audiences(
        payload.get("audiences")
        or payload.get("audience")
        or payload.get("school_levels")
        or payload.get("school_level")
    )
    if explicit:
        return explicit

    label = str(payload.get("team") or payload.get("title") or "").strip()
    if source == "custom":
        return list(AUDIENCES)
    if looks_middle_school(label):
        return ["middle-school"]
    if source in {"athletics", "arts"}:
        return ["upper-school"]
    return list(AUDIENCES)


@dataclass
class WeeklyEventRecord:
    id: str
    title: str
    start_date: str
    end_date: str
    time_text: str
    location: str
    category: str
    source: str
    audiences: list[str]
    kind: str = "event"
    subtitle: str = ""
    description: str = ""
    link: str = ""
    badge: str = "EVENT"
    priority: int = 3
    accent: str = SOURCE_ACCENTS["custom"]
    source_id: str = ""
    status: str = "active"
    team: str = ""
    opponent: str = ""
    is_home: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_firestore(self) -> dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeeklyEventRecord":
        data = dict(payload)
        return cls(
            id=str(data.get("id", "")).strip() or uuid4().hex,
            title=str(data.get("title", "Untitled Event")).strip() or "Untitled Event",
            start_date=str(data.get("start_date") or data.get("date") or "").strip(),
            end_date=str(data.get("end_date") or data.get("start_date") or data.get("date") or "").strip(),
            time_text=str(data.get("time_text") or data.get("time") or "TBA").strip() or "TBA",
            location=str(data.get("location", "On Campus")).strip() or "On Campus",
            category=str(data.get("category", "School Event")).strip() or "School Event",
            source=str(data.get("source", "custom")).strip() or "custom",
            audiences=normalize_audiences(data.get("audiences")) or list(AUDIENCES),
            kind=str(data.get("kind", "event")).strip() or "event",
            subtitle=str(data.get("subtitle", "")).strip(),
            description=str(data.get("description", "")).strip(),
            link=str(data.get("link", "")).strip(),
            badge=str(data.get("badge", "EVENT")).strip().upper() or "EVENT",
            priority=max(1, min(int(data.get("priority", 3)), 5)),
            accent=str(data.get("accent", SOURCE_ACCENTS["custom"])).strip() or SOURCE_ACCENTS["custom"],
            source_id=str(data.get("source_id", "")).strip(),
            status=str(data.get("status", "active")).strip() or "active",
            team=str(data.get("team", "")).strip(),
            opponent=str(data.get("opponent", "")).strip(),
            is_home=bool(data.get("is_home", True)),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
            created_at=str(data.get("created_at", "")).strip(),
            updated_at=str(data.get("updated_at", "")).strip(),
        )


@dataclass
class WeeklyDraftRecord:
    week_id: str
    start_date: str
    end_date: str
    heading: str = DEFAULT_HEADING
    status: str = DEFAULT_STATUS
    approval: dict[str, Any] = field(default_factory=default_approval_state)
    sent: dict[str, Any] = field(default_factory=default_sent_state)
    notes: str = ""
    events: list[WeeklyEventRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        return payload

    def to_firestore(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("events", None)
        return payload
