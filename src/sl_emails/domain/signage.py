from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..services.event_shapes import PosterEvent, poster_event_from_dict


@dataclass
class SignageEventRecord:
    title: str
    date: str
    time: str
    location: str
    category: str
    source: str
    subtitle: str = ""
    badge: str = ""
    priority: int = 2
    accent: str = ""
    audiences: list[str] = field(default_factory=list)
    team: str = ""
    opponent: str = ""
    is_home: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_poster_event(cls, event: PosterEvent) -> "SignageEventRecord":
        return cls(
            title=event.title,
            date=event.date,
            time=event.time,
            location=event.location,
            category=event.category,
            source=event.source,
            subtitle=event.subtitle,
            badge=event.badge,
            priority=event.priority,
            accent=event.accent,
            audiences=list(event.audiences),
            team=event.team,
            opponent=event.opponent,
            is_home=event.is_home,
            metadata=dict(event.metadata),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SignageEventRecord":
        event = poster_event_from_dict(payload)
        return cls.from_poster_event(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "category": self.category,
            "source": self.source,
            "badge": self.badge,
            "priority": self.priority,
            "accent": self.accent,
            "audiences": list(self.audiences),
            "team": self.team,
            "opponent": self.opponent,
            "is_home": self.is_home,
            "metadata": dict(self.metadata),
        }

    def to_poster_event(self) -> PosterEvent:
        return poster_event_from_dict(self.to_dict())


@dataclass
class SignageDayRecord:
    day_id: str
    events: list[SignageEventRecord]
    source_summary: dict[str, int]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SignageDayRecord":
        return cls(
            day_id=str(payload.get("date") or payload.get("day_id") or "").strip(),
            events=[
                SignageEventRecord.from_dict(item)
                for item in (payload.get("events") if isinstance(payload.get("events"), list) else [])
                if isinstance(item, dict)
            ],
            source_summary={
                "athletics_events": int(((payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else {}) or {}).get("athletics_events", 0) or 0),
                "arts_events": int(((payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else {}) or {}).get("arts_events", 0) or 0),
                "total_events": int(((payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else {}) or {}).get("total_events", 0) or 0),
            },
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
            created_at=str(payload.get("created_at") or "").strip(),
            updated_at=str(payload.get("updated_at") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.day_id,
            "events": [event.to_dict() for event in self.events],
            "source_summary": {
                "athletics_events": int(self.source_summary.get("athletics_events", 0) or 0),
                "arts_events": int(self.source_summary.get("arts_events", 0) or 0),
                "total_events": int(self.source_summary.get("total_events", 0) or 0),
            },
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def poster_events(self) -> list[PosterEvent]:
        return [event.to_poster_event() for event in self.events]
