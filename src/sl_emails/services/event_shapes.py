from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import hashlib
import re
from typing import Any, Callable, Iterable

from ..domain.dates import event_date_for_sort, iso_to_date, normalize_to_iso_date, time_for_sort, utc_now_iso
from ..domain.styling import SOURCE_ACCENTS, accent_from_sport, source_order
from ..domain.weekly import infer_audiences


@dataclass
class PosterEvent:
    title: str
    date: str
    time: str
    location: str
    category: str
    source: str
    subtitle: str = ""
    badge: str = ""
    priority: int = 2
    accent: str = SOURCE_ACCENTS["athletics"]
    audiences: list[str] = field(default_factory=list)
    team: str = ""
    opponent: str = ""
    is_home: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def poster_event_from_dict(payload: dict[str, Any]) -> PosterEvent:
    return PosterEvent(
        title=str(payload.get("title", "")).strip() or "Untitled Event",
        subtitle=str(payload.get("subtitle", "")).strip(),
        date=str(payload.get("date", "")).strip(),
        time=str(payload.get("time", "TBA")).strip() or "TBA",
        location=str(payload.get("location", "On Campus")).strip() or "On Campus",
        category=str(payload.get("category", "School Event")).strip() or "School Event",
        source=str(payload.get("source", "custom")).strip() or "custom",
        badge=str(payload.get("badge", "EVENT")).strip().upper() or "EVENT",
        priority=max(1, min(int(payload.get("priority", 2)), 5)),
        accent=str(payload.get("accent", SOURCE_ACCENTS["athletics"])).strip() or SOURCE_ACCENTS["athletics"],
        audiences=payload.get("audiences") if isinstance(payload.get("audiences"), list) else [],
        team=str(payload.get("team", "")).strip(),
        opponent=str(payload.get("opponent", "")).strip(),
        is_home=bool(payload.get("is_home", True)),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    )


def priority_from_source_event(event: Any, is_varsity_game: Callable[[str], bool]) -> int:
    if getattr(event, "event_type", "game") == "arts":
        return 4
    team = getattr(event, "team", "")
    is_home = bool(getattr(event, "is_home", False))
    is_varsity = is_varsity_game(team)
    if is_home and is_varsity:
        return 4
    if is_home or is_varsity:
        return 3
    return 2


def audiences_for_bucket(school_bucket: str) -> list[str]:
    return ["middle-school"] if school_bucket == "middle_school" else ["upper-school"]


def source_event_to_weekly_event_payload(
    event: Any,
    *,
    school_bucket: str,
    is_varsity_game: Callable[[str], bool],
    timestamp: str,
) -> dict[str, Any]:
    event_type = getattr(event, "event_type", "game")
    config = event.get_sport_config() if hasattr(event, "get_sport_config") else {}
    accent = config.get("accent_color") or config.get("border_color") or SOURCE_ACCENTS["athletics"]

    if event_type == "arts":
        title = getattr(event, "title", "Untitled Event")
        category = getattr(event, "category", "arts")
        unique_key = "|".join(
            [event_type, title, getattr(event, "date", ""), getattr(event, "time", ""), getattr(event, "location", ""), category, school_bucket]
        )
        event_id = hashlib.sha1(unique_key.encode("utf-8")).hexdigest()[:16]
        return {
            "id": event_id,
            "title": title,
            "start_date": normalize_to_iso_date(getattr(event, "date", "")),
            "end_date": normalize_to_iso_date(getattr(event, "date", "")),
            "time_text": getattr(event, "time", "TBA"),
            "location": getattr(event, "location", "On Campus"),
            "category": category.title(),
            "source": "arts",
            "audiences": audiences_for_bucket(school_bucket),
            "kind": "event",
            "subtitle": category.title(),
            "description": "",
            "link": "",
            "badge": "EVENT",
            "priority": 4,
            "accent": accent,
            "source_id": event_id,
            "status": "active",
            "team": getattr(event, "team", title),
            "opponent": "",
            "is_home": True,
            "metadata": {
                "school_bucket": school_bucket,
                "source_type": "arts",
                "raw_category": category,
            },
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    team = getattr(event, "team", "Team Event")
    opponent = getattr(event, "opponent", "TBA")
    is_home = bool(getattr(event, "is_home", False))
    sport = getattr(event, "sport", "Athletics")
    unique_key = "|".join(
        [event_type, team, opponent, getattr(event, "date", ""), getattr(event, "time", ""), getattr(event, "location", ""), str(is_home), sport, school_bucket]
    )
    event_id = hashlib.sha1(unique_key.encode("utf-8")).hexdigest()[:16]
    return {
        "id": event_id,
        "title": team,
        "start_date": normalize_to_iso_date(getattr(event, "date", "")),
        "end_date": normalize_to_iso_date(getattr(event, "date", "")),
        "time_text": getattr(event, "time", "TBA"),
        "location": getattr(event, "location", "Location TBA"),
        "category": (sport or "Athletics").title(),
        "source": "athletics",
        "audiences": audiences_for_bucket(school_bucket),
        "kind": "game",
        "subtitle": f"vs. {opponent}" if opponent else "Opponent TBA",
        "description": "",
        "link": "",
        "badge": "HOME" if is_home else "AWAY",
        "priority": priority_from_source_event(event, is_varsity_game),
        "accent": accent,
        "source_id": event_id,
        "status": "active",
        "team": team,
        "opponent": opponent,
        "is_home": is_home,
        "metadata": {
            "school_bucket": school_bucket,
            "source_type": "game",
            "sport": sport,
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def source_event_to_poster_event(source_event: Any, is_varsity_game: Callable[[str], bool]) -> PosterEvent:
    event_type = getattr(source_event, "event_type", "game")
    if event_type == "arts":
        title = getattr(source_event, "title", "Untitled Event")
        category = getattr(source_event, "category", "arts")
        team = getattr(source_event, "team", title)
        return PosterEvent(
            title=title,
            subtitle=category.title(),
            date=normalize_to_iso_date(getattr(source_event, "date", "")),
            time=getattr(source_event, "time", "TBA"),
            location=getattr(source_event, "location", "On Campus"),
            category=category.title(),
            source="arts",
            badge="EVENT",
            priority=4,
            accent=SOURCE_ACCENTS["arts"],
            audiences=infer_audiences({"title": title, "team": team, "audiences": getattr(source_event, "audiences", None)}, source="arts"),
            team=team,
            metadata={"source_type": "arts", "raw_category": category},
        )

    team = getattr(source_event, "team", "Team Event")
    opponent = getattr(source_event, "opponent", "TBA")
    is_home = bool(getattr(source_event, "is_home", False))
    sport = getattr(source_event, "sport", "Athletics")
    return PosterEvent(
        title=team,
        subtitle=f"vs. {opponent}" if opponent else "Opponent TBA",
        date=normalize_to_iso_date(getattr(source_event, "date", "")),
        time=getattr(source_event, "time", "TBA"),
        location=getattr(source_event, "location", "Location TBA"),
        category=(sport or "Athletics").title(),
        source="athletics",
        badge="HOME" if is_home else "AWAY",
        priority=priority_from_source_event(source_event, is_varsity_game),
        accent=accent_from_sport(sport, "athletics"),
        audiences=infer_audiences({"title": team, "team": team, "audiences": getattr(source_event, "audiences", None)}, source="athletics"),
        team=team,
        opponent=opponent,
        is_home=is_home,
        metadata={"source_type": "game", "sport": sport},
    )


def normalize_custom_event(payload: dict[str, Any]) -> PosterEvent:
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValueError("Custom event title is required")
    date_value = str(payload.get("date", "")).strip()
    if not date_value:
        raise ValueError("Custom event date is required")
    iso_to_date(date_value)

    category = str(payload.get("category", "School Event")).strip() or "School Event"
    priority = max(1, min(int(payload.get("priority", 3)), 5))
    accent_raw = str(payload.get("accent", "")).strip()
    accent = accent_raw if re.fullmatch(r"#[0-9A-Fa-f]{6}", accent_raw) else SOURCE_ACCENTS["custom"]
    return PosterEvent(
        title=title,
        subtitle=str(payload.get("subtitle", category)).strip(),
        date=date_value,
        time=str(payload.get("time", "TBA")).strip() or "TBA",
        location=str(payload.get("location", "On Campus")).strip() or "On Campus",
        category=category,
        source="custom",
        badge=str(payload.get("badge", "SPECIAL")).strip().upper() or "SPECIAL",
        priority=priority,
        accent=accent,
        audiences=["middle-school", "upper-school"],
        team=title,
        metadata={"source_type": "custom"},
    )


def sort_poster_events(events: Iterable[PosterEvent]) -> list[PosterEvent]:
    return sorted(
        events,
        key=lambda event: (
            event_date_for_sort(event.date),
            time_for_sort(event.time),
            -event.priority,
            source_order(event.source),
            event.title.lower(),
        ),
    )


def merge_poster_events(base_events: Iterable[PosterEvent], custom_events: Iterable[dict[str, Any]]) -> list[PosterEvent]:
    merged = list(base_events)
    for event_payload in custom_events:
        merged.append(normalize_custom_event(event_payload))
    return sort_poster_events(merged)


def fetch_week_events(
    start: date,
    end: date,
    *,
    scrape_athletics_schedule: Callable[[str, str], list[Any]],
    fetch_arts_events: Callable[[str, str], list[Any]],
    is_varsity_game: Callable[[str], bool],
) -> list[PosterEvent]:
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    source_events = scrape_athletics_schedule(start_str, end_str) + fetch_arts_events(start_str, end_str)
    return sort_poster_events(source_event_to_poster_event(event, is_varsity_game) for event in source_events)


def poster_event_to_weekly_event_payload(event: PosterEvent, *, timestamp: str | None = None) -> dict[str, Any]:
    resolved_timestamp = timestamp or utc_now_iso()
    audiences = list(event.audiences) or infer_audiences({"title": event.title, "team": event.team}, source=event.source)
    unique_key = "|".join(
        [
            event.source,
            event.title,
            event.subtitle,
            event.date,
            event.time,
            event.location,
            event.category,
            ",".join(sorted(audiences)),
            str(event.is_home),
        ]
    )
    event_id = hashlib.sha1(unique_key.encode("utf-8")).hexdigest()[:16]
    kind = "game" if event.source == "athletics" else "event"
    opponent = event.opponent or (
        event.subtitle.removeprefix("vs. ").strip() if kind == "game" and event.subtitle.startswith("vs. ") else ""
    )
    metadata = dict(event.metadata)
    metadata.setdefault("source_type", "game" if kind == "game" else event.source)

    return {
        "id": event_id,
        "title": event.title,
        "start_date": event.date,
        "end_date": event.date,
        "time_text": event.time,
        "location": event.location,
        "category": event.category,
        "source": event.source,
        "audiences": audiences,
        "kind": kind,
        "subtitle": event.subtitle,
        "description": "",
        "link": "",
        "badge": event.badge,
        "priority": event.priority,
        "accent": event.accent,
        "source_id": event_id,
        "status": "active",
        "team": event.team or event.title,
        "opponent": opponent,
        "is_home": event.is_home,
        "metadata": metadata,
        "created_at": resolved_timestamp,
        "updated_at": resolved_timestamp,
    }
