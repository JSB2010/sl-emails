from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sl_emails.ingest.generate_games import fetch_arts_events, is_varsity_game, scrape_athletics_schedule
from sl_emails.services.event_shapes import PosterEvent, SourceFetchStatus, WeekEventsFetchResult, fetch_week_events

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
    source_health: list[dict[str, Any]]


class SignageSourceFetchError(RuntimeError):
    def __init__(self, message: str, *, source_health: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.source_health = source_health


def signage_source_summary(events: list[PosterEvent]) -> dict[str, int]:
    athletics = sum(1 for event in events if event.source == "athletics")
    arts = sum(1 for event in events if event.source == "arts")
    return {
        "athletics_events": athletics,
        "arts_events": arts,
        "total_events": len(events),
    }


def _source_failure_message(fetch_result: WeekEventsFetchResult) -> str:
    failed = [
        f"{status.source}: {status.error or 'fetch failed'}"
        for status in fetch_result.source_statuses
        if not status.ok
    ]
    return "Unable to refresh signage because one or more source fetches failed. " + "; ".join(failed)


def _coerce_fetch_result(fetch_result: Any) -> WeekEventsFetchResult:
    if isinstance(fetch_result, WeekEventsFetchResult):
        return fetch_result
    events = list(fetch_result) if isinstance(fetch_result, list) else []
    fetched_at = utc_now_iso()
    return WeekEventsFetchResult(
        events=events,
        source_statuses=[
            SourceFetchStatus(source="athletics", ok=True, event_count=sum(1 for event in events if getattr(event, "source", "") == "athletics"), error="", fetched_at=fetched_at),
            SourceFetchStatus(source="arts", ok=True, event_count=sum(1 for event in events if getattr(event, "source", "") == "arts"), error="", fetched_at=fetched_at),
        ],
    )


def fetch_signage_events(day_id: str) -> WeekEventsFetchResult:
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
    fetch_result = _coerce_fetch_result(fetch_signage_events(day_id))
    if not fetch_result.ok:
        raise SignageSourceFetchError(
            _source_failure_message(fetch_result),
            source_health=fetch_result.status_dicts(),
        )

    events = fetch_result.events
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
        source_health=fetch_result.status_dicts(),
    )
