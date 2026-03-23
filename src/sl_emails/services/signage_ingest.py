from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sl_emails.ingest.generate_games import fetch_arts_events, is_varsity_game, scrape_athletics_schedule
from sl_emails.services.event_shapes import PosterEvent, fetch_week_events

from ..domain.dates import iso_to_date, utc_now_iso
from ..domain.signage import SignageEventRecord
from .signage_store import SignageStore


@dataclass
class SignageRefreshResult:
    day_id: str
    action: str
    reason: str
    day: Any
    source_summary: dict[str, int]


def signage_source_summary(events: list[PosterEvent]) -> dict[str, int]:
    athletics = sum(1 for event in events if event.source == "athletics")
    arts = sum(1 for event in events if event.source == "arts")
    return {
        "athletics_events": athletics,
        "arts_events": arts,
        "total_events": len(events),
    }


def fetch_signage_events(day_id: str) -> list[PosterEvent]:
    target_day = iso_to_date(day_id)
    return fetch_week_events(
        target_day,
        target_day,
        scrape_athletics_schedule=scrape_athletics_schedule,
        fetch_arts_events=fetch_arts_events,
        is_varsity_game=is_varsity_game,
    )


def refresh_signage_day(store: SignageStore, day_id: str, *, actor: str = "system") -> SignageRefreshResult:
    existing = store.get_day(day_id)
    events = fetch_signage_events(day_id)
    action = "created" if existing is None else "refreshed"
    reason = "created_from_sources" if existing is None else "replaced_existing_snapshot"
    timestamp = utc_now_iso()
    summary = signage_source_summary(events)
    day = store.save_day(
        day_id,
        {
            "events": [SignageEventRecord.from_poster_event(event).to_dict() for event in events],
            "source_summary": summary,
            "metadata": {
                **(dict(existing.metadata) if existing else {}),
                "ingest": {
                    "status": "success",
                    "action": action,
                    "reason": reason,
                    "actor": actor,
                    "occurred_at": timestamp,
                },
            },
        },
    )
    return SignageRefreshResult(
        day_id=day_id,
        action=action,
        reason=reason,
        day=day,
        source_summary=summary,
    )
