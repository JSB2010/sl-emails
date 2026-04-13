from __future__ import annotations

import re
from typing import Any

from ..domain.dates import display_date, overlap_dates
from ..domain.weekly import WeeklyDraftRecord


def copy_overrides_for_audience(week: WeeklyDraftRecord, audience: str) -> dict[str, str]:
    overrides = dict(week.copy_overrides or {})
    audience_overrides = (week.copy_overrides_by_audience or {}).get(audience)
    if isinstance(audience_overrides, dict):
        overrides.update({key: str(value or "").strip() for key, value in audience_overrides.items()})
    return overrides


def renderable_events_for_audience(
    week: WeeklyDraftRecord,
    audience: str,
    *,
    generate_games_module: Any,
) -> list[Any]:
    rendered: list[Any] = []
    for event in week.events:
        if str(event.status or "active").strip().lower() in {"hidden", "inactive", "archived"}:
            continue
        if audience not in event.audiences:
            continue
        for current_date in overlap_dates(event.start_date, event.end_date, week.start_date, week.end_date):
            current_display_date = display_date(current_date)
            if event.kind == "game":
                rendered.append(
                    generate_games_module.Game(
                        team=event.team or event.title,
                        opponent=event.opponent,
                        date=current_display_date,
                        time=event.time_text,
                        location=event.location,
                        is_home=event.is_home,
                        sport=event.category,
                        description=event.description,
                        link=event.link,
                        icon=event.icon,
                    )
                )
            else:
                rendered.append(
                    generate_games_module.Event(
                        title=event.title,
                        date=current_display_date,
                        time=event.time_text,
                        location=event.location,
                        category=event.category,
                        description=event.description,
                        link=event.link,
                        icon=event.icon,
                    )
                )
    return rendered


def default_subject_for_date_range(date_range: str, *, has_arts: bool) -> str:
    base = "Sports and Performances This Week" if has_arts else "Sports This Week"
    cleaned_range = re.sub(r",\s*\d{4}$", "", date_range).replace("–", " - ")
    return f"{base}: {cleaned_range}"


def extract_subject(html: str) -> str:
    has_arts = bool(re.search(r'<meta name="has-arts-events" content="true"', html, flags=re.IGNORECASE))
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not title_match:
        return default_subject_for_date_range("", has_arts=has_arts).rstrip(": ")
    date_match = re.search(r"\(([^)]+)\)", title_match.group(1))
    if not date_match:
        return title_match.group(1).strip()
    return default_subject_for_date_range(date_match.group(1), has_arts=has_arts)


def build_weekly_email_outputs(
    week: WeeklyDraftRecord,
    *,
    generate_games_module: Any,
    icon_base_url: str = "",
) -> dict[str, dict[str, Any]]:
    date_range = generate_games_module.format_date_range(week.start_date, week.end_date)
    outputs: dict[str, dict[str, Any]] = {}
    for audience, school_level in (("middle-school", "Middle School"), ("upper-school", "Upper School")):
        renderable_events = renderable_events_for_audience(week, audience, generate_games_module=generate_games_module)
        grouped = generate_games_module.group_games_by_date(renderable_events)
        sport_labels = sorted({item.sport for item in renderable_events if getattr(item, "sport", "")})
        sports_list = ", ".join(label.title() for label in sport_labels) or "School Events"
        has_arts = any(getattr(item, "event_type", "") == "arts" for item in renderable_events)
        default_subject = default_subject_for_date_range(date_range, has_arts=has_arts)
        subject = str(week.subject_overrides.get(audience) or "").strip() or default_subject
        html = generate_games_module.generate_html_email(
            grouped,
            date_range,
            sports_list,
            week.start_date,
            week.end_date,
            school_level,
            heading=week.heading,
            intro_note=week.notes,
            email_subject=subject,
            copy_overrides=copy_overrides_for_audience(week, audience),
            icon_base_url=icon_base_url,
        )
        outputs[audience] = {
            "audience": audience,
            "subject": subject,
            "default_subject": default_subject,
            "html": html,
            "source_event_count": sum(
                1
                for event in week.events
                if audience in event.audiences and str(event.status or "active").strip().lower() not in {"hidden", "inactive", "archived"}
            ),
            "rendered_occurrence_count": len(renderable_events),
        }
    return outputs
