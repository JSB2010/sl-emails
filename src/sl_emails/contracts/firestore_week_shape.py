from __future__ import annotations

from typing import Any, Callable

from ..domain.dates import event_date_for_sort, format_email_date_range, time_for_sort, utc_now_iso
from ..domain.weekly import DEFAULT_HEADING, default_approval_state, default_audience_copy_overrides, default_copy_overrides, default_delivery_state, default_sent_state
from ..services.event_shapes import source_event_to_weekly_event_payload


EMAIL_WEEKS_COLLECTION = "emailWeeks"
EVENTS_SUBCOLLECTION = "events"


def build_week_draft_document(
    *,
    start_date: str,
    end_date: str,
    events: list[Any],
    summary: dict[str, Any],
    run_context: dict[str, Any],
    is_middle_school_game: Callable[[str], bool],
    is_varsity_game: Callable[[str], bool],
) -> dict[str, Any]:
    timestamp = utc_now_iso()
    normalized_events = []
    for event in events:
        school_bucket = "middle_school" if is_middle_school_game(getattr(event, "team", "")) else "upper_school"
        normalized_events.append(
            source_event_to_weekly_event_payload(
                event,
                school_bucket=school_bucket,
                is_varsity_game=is_varsity_game,
                timestamp=timestamp,
            )
        )

    normalized_events.sort(
        key=lambda event: (
            event_date_for_sort(event["start_date"]),
            time_for_sort(event["time_text"]),
            event["audiences"][0],
            event["title"].lower(),
        )
    )

    return {
        "weekKey": start_date,
        "week": {
            "start_date": start_date,
            "end_date": end_date,
            "heading": DEFAULT_HEADING,
            "status": "draft",
            "approval": default_approval_state(),
            "sent": default_sent_state(),
            "notes": "",
            "subject_overrides": {},
            "delivery": default_delivery_state(start_date),
            "copy_overrides": default_copy_overrides(),
            "copy_overrides_by_audience": default_audience_copy_overrides(),
            "created_at": timestamp,
            "updated_at": timestamp,
            "week_label": format_email_date_range(start_date, end_date),
            "source_summary": summary,
            "ingest_context": {
                "runner": "github-actions" if run_context.get("githubRunId") else "local",
                "last_ingested_at": timestamp,
                **run_context,
            },
        },
        "events": normalized_events,
    }
