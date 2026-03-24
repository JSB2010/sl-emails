from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sl_emails.domain.dates import iso_to_date, utc_now_iso, week_end_for
from sl_emails.ingest.generate_games import fetch_arts_events, is_varsity_game, scrape_athletics_schedule
from sl_emails.services.event_shapes import fetch_week_events, poster_event_to_weekly_event_payload
from sl_emails.services.weekly_store import WeeklyEmailStore


@dataclass
class WeeklyIngestResult:
    week_id: str
    action: str
    reason: str
    week: Any
    source_summary: dict[str, int]


def _source_summary(events: list[Any]) -> dict[str, int]:
    athletics = sum(1 for event in events if event.source == "athletics")
    arts = sum(1 for event in events if event.source == "arts")
    return {
        "athletics_events": athletics,
        "arts_events": arts,
        "total_events": len(events),
    }


def _build_source_payload(
    *,
    week_id: str,
    heading: str,
    notes: str,
    subject_overrides: dict[str, str],
    preserved_events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    start_date = iso_to_date(week_id)
    end_date = iso_to_date(week_end_for(week_id))
    fetched_events = fetch_week_events(
        start_date,
        end_date,
        scrape_athletics_schedule=scrape_athletics_schedule,
        fetch_arts_events=fetch_arts_events,
        is_varsity_game=is_varsity_game,
    )
    timestamp = utc_now_iso()
    source_events = [poster_event_to_weekly_event_payload(event, timestamp=timestamp) for event in fetched_events]

    return (
        {
            "start_date": week_id,
            "end_date": end_date.isoformat(),
            "heading": heading,
            "notes": notes,
            "subject_overrides": subject_overrides,
            "events": [*preserved_events, *source_events],
        },
        _source_summary(fetched_events),
    )


def scheduled_ingest_week(store: WeeklyEmailStore, week_id: str) -> WeeklyIngestResult:
    existing = store.get_week(week_id)
    if existing is not None:
        return WeeklyIngestResult(
            week_id=week_id,
            action="skipped",
            reason="existing_draft",
            week=existing,
            source_summary={"athletics_events": 0, "arts_events": 0, "total_events": 0},
        )

    payload, source_summary = _build_source_payload(
        week_id=week_id,
        heading="This Week at Kent Denver",
        notes="",
        subject_overrides={},
        preserved_events=[],
    )
    created_week = store.create_week_if_missing(week_id, payload)
    if created_week is None:
        existing = store.get_week(week_id)
        if existing is None:
            raise RuntimeError(f"Weekly draft {week_id} could not be loaded after create-if-missing")
        return WeeklyIngestResult(
            week_id=week_id,
            action="skipped",
            reason="existing_draft",
            week=existing,
            source_summary={"athletics_events": 0, "arts_events": 0, "total_events": 0},
        )

    week = created_week
    return WeeklyIngestResult(
        week_id=week_id,
        action="created",
        reason="created_from_sources",
        week=week,
        source_summary=source_summary,
    )


def source_refresh_week(store: WeeklyEmailStore, week_id: str) -> WeeklyIngestResult:
    existing = store.get_week(week_id)
    preserved_events: list[dict[str, Any]] = []
    heading = "This Week at Kent Denver"
    notes = ""
    subject_overrides: dict[str, str] = {}
    action = "created"
    reason = "created_from_sources"

    if existing is not None:
        heading = existing.heading
        notes = existing.notes
        subject_overrides = dict(existing.subject_overrides)
        preserved_events = [event.to_dict() for event in existing.events if event.source == "custom"]
        action = "refreshed"
        reason = "replaced_source_events_preserved_custom"
        store.reset_week_send(week_id)

    payload, source_summary = _build_source_payload(
        week_id=week_id,
        heading=heading,
        notes=notes,
        subject_overrides=subject_overrides,
        preserved_events=preserved_events,
    )
    week = store.save_week(week_id, payload)
    return WeeklyIngestResult(
        week_id=week_id,
        action=action,
        reason=reason,
        week=week,
        source_summary=source_summary,
    )
