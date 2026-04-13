from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any
from uuid import uuid4

from .dates import default_send_date_for_week, iso_to_date, week_end_for, week_start_for
from .iconography import normalize_icon_key
from .styling import SOURCE_ACCENTS


AUDIENCES = ("middle-school", "upper-school")
DEFAULT_HEADING = "This Week at Kent Denver"
DEFAULT_STATUS = "draft"
DEFAULT_SEND_TIME = "16:00"


def default_copy_overrides() -> dict[str, Any]:
    return {
        "hero_text": "",
        "intro_title": "",
        "intro_text": "",
        "spotlight_label": "",
        "schedule_label": "",
        "also_on_schedule_label": "",
        "empty_day_template": "",
        "cta_eyebrow": "",
        "cta_title": "",
        "cta_text": "",
    }


def default_audience_copy_overrides() -> dict[str, dict[str, Any]]:
    return {audience: default_copy_overrides() for audience in AUDIENCES}


def normalize_copy_overrides(payload: Any) -> dict[str, str]:
    defaults = default_copy_overrides()
    if not isinstance(payload, dict):
        return defaults
    normalized = dict(defaults)
    for key in defaults:
        normalized[key] = str(payload.get(key) or "").strip()
    return normalized


def normalize_audience_copy_overrides(payload: Any, *, fallback: Any | None = None) -> dict[str, dict[str, str]]:
    shared_fallback = normalize_copy_overrides(fallback)
    normalized: dict[str, dict[str, str]] = {}
    source = payload if isinstance(payload, dict) else {}
    for audience in AUDIENCES:
        audience_payload = source.get(audience)
        merged = dict(shared_fallback)
        if isinstance(audience_payload, dict):
            for key in default_copy_overrides():
                if key in audience_payload:
                    merged[key] = str(audience_payload.get(key) or "").strip()
        normalized[audience] = merged
    return normalized


def default_delivery_state(week_id: str = "", *, updated_by: str = "") -> dict[str, Any]:
    normalized_week_id = week_start_for(week_id) if week_id else ""
    return {
        "mode": "default",
        "send_on": default_send_date_for_week(normalized_week_id) if normalized_week_id else "",
        "send_time": DEFAULT_SEND_TIME,
        "updated_at": "",
        "updated_by": updated_by,
    }


def normalize_delivery(payload: Any, *, week_id: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    baseline = default_delivery_state(week_id)
    if isinstance(fallback, dict):
        baseline.update(
            {
                "mode": str(fallback.get("mode") or baseline["mode"]).strip().lower() or baseline["mode"],
                "send_on": str(fallback.get("send_on") or baseline["send_on"]).strip() or baseline["send_on"],
                "send_time": str(fallback.get("send_time") or baseline["send_time"]).strip() or baseline["send_time"],
                "updated_at": str(fallback.get("updated_at") or "").strip(),
                "updated_by": str(fallback.get("updated_by") or "").strip(),
            }
        )

    if not isinstance(payload, dict):
        payload = {}

    mode = str(payload.get("mode") or baseline["mode"]).strip().lower() or baseline["mode"]
    if mode not in {"default", "postpone", "skip"}:
        mode = baseline["mode"]

    send_time = str(payload.get("send_time") or baseline["send_time"]).strip() or baseline["send_time"]
    send_on = str(payload.get("send_on") or "").strip()
    monday = week_start_for(week_id)
    if mode == "default":
        send_on = default_send_date_for_week(monday)
    elif mode == "postpone":
        allowed = {(iso_to_date(monday) + timedelta(days=offset)).isoformat() for offset in range(4)}
        if send_on not in allowed:
            fallback_send_on = str(baseline.get("send_on") or "")
            send_on = fallback_send_on if fallback_send_on in allowed else monday
    else:
        send_on = ""

    return {
        "mode": mode,
        "send_on": send_on,
        "send_time": send_time,
        "updated_at": str(payload.get("updated_at") or baseline.get("updated_at") or "").strip(),
        "updated_by": str(payload.get("updated_by") or baseline.get("updated_by") or "").strip(),
    }


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


def normalize_subject_overrides(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in raw.items():
        audience_matches = normalize_audiences(key)
        if not audience_matches:
            continue
        text = str(value or "").strip()
        if not text:
            continue
        normalized[audience_matches[0]] = text
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
    icon: str = ""
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
            icon=normalize_icon_key(str(data.get("icon", "")).strip()),
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
    subject_overrides: dict[str, str] = field(default_factory=dict)
    delivery: dict[str, Any] = field(default_factory=dict)
    copy_overrides: dict[str, str] = field(default_factory=default_copy_overrides)
    copy_overrides_by_audience: dict[str, dict[str, str]] = field(default_factory=default_audience_copy_overrides)
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
