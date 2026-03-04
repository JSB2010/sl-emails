#!/usr/bin/env python3
"""Shared event + daily carousel poster generation utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from typing import Any, Iterable
import argparse
import json
import re
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SPORTS_EMAILS_DIR = ROOT_DIR / "sports-emails"


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
    accent: str = "#0C3A6B"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def poster_event_from_dict(payload: dict[str, Any]) -> PosterEvent:
    """Deserialize an event sent by the web UI."""
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
        accent=str(payload.get("accent", "#0C3A6B")).strip() or "#0C3A6B",
    )


_SPORT_COLOR_MAP = {
    "soccer": "#0066FF",
    "football": "#A11919",
    "tennis": "#13CF97",
    "golf": "#F2B900",
    "cross country": "#8B5CF6",
    "field hockey": "#EC4899",
    "volleyball": "#F59E0B",
    "basketball": "#F97316",
    "lacrosse": "#10B981",
    "baseball": "#3B82F6",
    "swimming": "#06B6D4",
    "track": "#8B5CF6",
    "ice hockey": "#64748B",
}

_DEFAULT_SOURCE_ACCENTS = {
    "athletics": "#0C3A6B",
    "arts": "#A11919",
    "custom": "#8C6A00",
}

KDS_LOGO_WEB_URL = (
    "https://cdn-assets-cloud.frontify.com/s3/frontify-cloud-files-us/"
    "eyJwYXRoIjoiZnJvbnRpZnlcL2FjY291bnRzXC9iNFwvNzU3NDlcL3Byb2plY3RzXC8xMDUwNjZc"
    "L2Fzc2V0c1wvYTNcLzY3NDA0OTZcLzlmYTY2NGYzZjhiOGI3YjY2ZDEwZDBkZGI5NjcxNmJmLTE2"
    "NTY4ODQyNjYucG5nIn0:frontify:0G-jY-31l0MCBnvlONY7KuK6-sTagdCay7zorKYJ6_o?width=600&format=png"
)


def _load_generate_games_module():
    """Load sports-emails generator lazily so tests can run without scraper deps."""
    if str(SPORTS_EMAILS_DIR) not in sys.path:
        sys.path.insert(0, str(SPORTS_EMAILS_DIR))

    import generate_games  # type: ignore  # noqa: PLC0415

    return generate_games


def _iso_to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _event_date_for_sort(value: str) -> date:
    """Parse source and custom date strings into a date object."""
    value = (value or "").strip()
    if not value:
        return date.max

    for fmt in ("%Y-%m-%d", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return date.max


def _normalize_to_iso_date(value: str) -> str:
    parsed = _event_date_for_sort(value)
    if parsed == date.max:
        return value
    return parsed.isoformat()


def _time_for_sort(value: str) -> time:
    value = (value or "").strip().upper()
    if not value or value in {"TBA", "ALL DAY"}:
        return time(23, 59)

    normalized = value.replace(".", "")
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue

    return time(23, 59)


def _source_order(source: str) -> int:
    order = {"athletics": 0, "arts": 1, "custom": 2}
    return order.get(source, 3)


def _source_label(source: str) -> str:
    labels = {
        "athletics": "Athletics",
        "arts": "Arts",
        "custom": "Custom",
    }
    return labels.get(source, source.title() if source else "Event")


def _priority_from_game(game: Any, is_varsity_game: Any) -> int:
    is_varsity = is_varsity_game(getattr(game, "team", ""))
    is_home = bool(getattr(game, "is_home", False))
    if is_home and is_varsity:
        return 4
    if is_home or is_varsity:
        return 3
    return 2


def _accent_from_sport(sport: str, source: str) -> str:
    sport_lower = (sport or "").lower()
    for key, color in _SPORT_COLOR_MAP.items():
        if key in sport_lower:
            return color
    return _DEFAULT_SOURCE_ACCENTS.get(source, "#0C3A6B")


def source_event_to_poster_event(source_event: Any, is_varsity_game: Any) -> PosterEvent:
    """Convert Game/Event objects from sports-emails into poster format."""
    event_type = getattr(source_event, "event_type", "game")

    if event_type == "arts":
        title = getattr(source_event, "title", "Untitled Event")
        category = getattr(source_event, "category", "arts")
        return PosterEvent(
            title=title,
            subtitle=category.title(),
            date=_normalize_to_iso_date(getattr(source_event, "date", "")),
            time=getattr(source_event, "time", "TBA"),
            location=getattr(source_event, "location", "On Campus"),
            category=category.title(),
            source="arts",
            badge="EVENT",
            priority=4,
            accent=_DEFAULT_SOURCE_ACCENTS["arts"],
        )

    team = getattr(source_event, "team", "Team Event")
    opponent = getattr(source_event, "opponent", "TBA")
    is_home = bool(getattr(source_event, "is_home", False))
    sport = getattr(source_event, "sport", "Athletics")

    return PosterEvent(
        title=team,
        subtitle=f"vs. {opponent}" if opponent else "Opponent TBA",
        date=_normalize_to_iso_date(getattr(source_event, "date", "")),
        time=getattr(source_event, "time", "TBA"),
        location=getattr(source_event, "location", "Location TBA"),
        category=(sport or "Athletics").title(),
        source="athletics",
        badge="HOME" if is_home else "AWAY",
        priority=_priority_from_game(source_event, is_varsity_game),
        accent=_accent_from_sport(sport, "athletics"),
    )


def get_week_bounds(
    mode: str = "next",
    *,
    today: date | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[date, date]:
    """Return Monday/Sunday for this or next week, or a custom range."""
    if start_date and end_date:
        start = _iso_to_date(start_date)
        end = _iso_to_date(end_date)
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        return start, end

    today = today or datetime.now().date()
    monday = today - timedelta(days=today.weekday())

    if mode == "next":
        monday = monday + timedelta(days=7)
    elif mode != "this":
        raise ValueError("mode must be 'this' or 'next'")

    sunday = monday + timedelta(days=6)
    return monday, sunday


def fetch_week_events(start: date, end: date) -> list[PosterEvent]:
    """Fetch athletics and arts events for the supplied date range."""
    generate_games = _load_generate_games_module()
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    games = generate_games.scrape_athletics_schedule(start_str, end_str)
    arts = generate_games.fetch_arts_events(start_str, end_str)

    events = [
        source_event_to_poster_event(event, generate_games.is_varsity_game)
        for event in (games + arts)
    ]
    return sort_events(events)


def normalize_custom_event(payload: dict[str, Any]) -> PosterEvent:
    """Convert an incoming custom event payload into canonical form."""
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValueError("Custom event title is required")

    date_value = str(payload.get("date", "")).strip()
    if not date_value:
        raise ValueError("Custom event date is required")

    _iso_to_date(date_value)

    category = str(payload.get("category", "School Event")).strip() or "School Event"
    priority = int(payload.get("priority", 3))
    priority = max(1, min(priority, 5))

    accent_raw = str(payload.get("accent", "")).strip()
    accent = accent_raw if re.fullmatch(r"#[0-9A-Fa-f]{6}", accent_raw) else _DEFAULT_SOURCE_ACCENTS["custom"]

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
    )


def sort_events(events: Iterable[PosterEvent]) -> list[PosterEvent]:
    return sorted(
        events,
        key=lambda event: (
            _event_date_for_sort(event.date),
            _time_for_sort(event.time),
            -event.priority,
            _source_order(event.source),
            event.title.lower(),
        ),
    )


def merge_events(base_events: Iterable[PosterEvent], custom_events: Iterable[dict[str, Any]]) -> list[PosterEvent]:
    merged = list(base_events)
    for event_payload in custom_events:
        merged.append(normalize_custom_event(event_payload))
    return sort_events(merged)


def _format_week_label(start: date, end: date) -> str:
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%B')} {start.day}-{end.day}, {start.year}"
    if start.year == end.year:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"


def _format_day_long(value: date) -> str:
    return value.strftime("%A, %B %-d") if sys.platform != "win32" else value.strftime("%A, %B %d").replace(" 0", " ")


def _layout_limits_day(total: int) -> tuple[int, int, str, int]:
    """Return cards, rows, density, and columns for one day slide."""
    if total <= 1:
        return total, 0, "spacious", 1
    if total <= 4:
        return total, 0, "balanced", 2
    if total <= 6:
        return total, 0, "compact", 2
    if total <= 9:
        return 6, total - 6, "compact", 2
    if total <= 14:
        return 6, min(total - 6, 8), "dense", 2
    return 4, min(total - 4, 10), "dense", 2


def build_daily_poster_model(
    day: date,
    events: list[PosterEvent],
    start: date,
    end: date,
    *,
    heading: str,
    slide_number: int,
    total_slides: int,
    logo_src: str = "/static/kd-logo.png",
) -> dict[str, Any]:
    """Build one day-focused slide model."""
    total_events = len(events)
    sorted_by_priority = sorted(
        events,
        key=lambda event: (-event.priority, _time_for_sort(event.time), event.title.lower()),
    )

    card_limit, row_limit, density, grid_columns = _layout_limits_day(total_events)
    featured_cards = sorted_by_priority[:card_limit]
    featured_ids = {id(event) for event in featured_cards}
    chrono_remaining = [event for event in events if id(event) not in featured_ids]
    list_rows = chrono_remaining[:row_limit]

    shown_total = len(featured_cards) + len(list_rows)
    overflow_count = max(0, total_events - shown_total)

    source_counts = {"athletics": 0, "arts": 0, "custom": 0}
    for event in events:
        source_counts[event.source] = source_counts.get(event.source, 0) + 1

    return {
        "heading": heading,
        "week_label": _format_week_label(start, end),
        "day_name": day.strftime("%A"),
        "day_long": _format_day_long(day),
        "date_iso": day.isoformat(),
        "slide_number": slide_number,
        "total_slides": total_slides,
        "logo_src": logo_src,
        "density": density,
        "grid_columns": grid_columns,
        "events_total": total_events,
        "featured_cards": featured_cards,
        "list_rows": list_rows,
        "overflow_count": overflow_count,
        "source_counts": source_counts,
    }


def build_daily_carousel_models(
    events: list[PosterEvent],
    start: date,
    end: date,
    *,
    heading: str = "This Week at Kent Denver",
    logo_src: str = "/static/kd-logo.png",
) -> list[dict[str, Any]]:
    """Build daily slide models for every day in the selected range."""
    sorted_events = sort_events(events)
    by_date: dict[str, list[PosterEvent]] = {}

    for event in sorted_events:
        parsed = _event_date_for_sort(event.date)
        if parsed == date.max or parsed < start or parsed > end:
            continue
        key = parsed.isoformat()
        by_date.setdefault(key, []).append(event)

    total_days = (end - start).days + 1
    models: list[dict[str, Any]] = []

    for offset in range(total_days):
        current = start + timedelta(days=offset)
        day_events = by_date.get(current.isoformat(), [])
        models.append(
            build_daily_poster_model(
                current,
                day_events,
                start,
                end,
                heading=heading,
                slide_number=offset + 1,
                total_slides=total_days,
                logo_src=logo_src,
            )
        )

    return models


def _event_card_html(event: PosterEvent) -> str:
    title = escape(event.title)
    subtitle = escape(event.subtitle)
    location = escape(event.location)
    badge = escape(event.badge)
    category = escape(event.category)
    time_label = escape(event.time)
    accent = escape(event.accent)

    subtitle_part = f'<p class="poster-card-subtitle">{subtitle}</p>' if event.subtitle else ""
    location_part = f'<span class="poster-card-location">{location}</span>' if event.location else ""

    return (
        '<article class="poster-card">'
        f'<div class="poster-card-top-bar" style="background:{accent};"></div>'
        '<div class="poster-card-body">'
        '<div class="poster-card-meta-row">'
        f'<span class="poster-badge" style="--badge-accent:{accent};">{badge}</span>'
        f'<span class="poster-time">{time_label}</span>'
        "</div>"
        '<div class="poster-card-main">'
        f'<h3 class="poster-card-title">{title}</h3>'
        f"{subtitle_part}"
        "</div>"
        '<div class="poster-card-bottom">'
        '<div class="poster-card-divider"></div>'
        '<div class="poster-card-footer-row">'
        f"{location_part}"
        f'<span class="poster-card-category">{category}</span>'
        "</div>"
        "</div>"
        "</div>"
        "</article>"
    )


def _event_row_html(event: PosterEvent) -> str:
    title = escape(event.title)
    subtitle = escape(event.subtitle)
    location = escape(event.location)
    time_label = escape(event.time)
    category = escape(event.category)
    accent = escape(event.accent)

    subtitle_part = f' <em>{subtitle}</em>' if event.subtitle else ""

    return (
        f'<li class="poster-row" style="--row-accent:{accent};">'
        f'<span class="poster-row-time">{time_label}</span>'
        f'<span class="poster-row-main"><strong>{title}</strong>{subtitle_part}</span>'
        '<div class="poster-row-right">'
        f'<span class="poster-row-location">{location}</span>'
        f'<span class="poster-row-cat">{category}</span>'
        "</div>"
        "</li>"
    )


def render_poster_fragment(model: dict[str, Any], *, poster_id: str = "instagram-poster") -> str:
    cards_html = "".join(_event_card_html(event) for event in model["featured_cards"])
    rows_html = "".join(_event_row_html(event) for event in model["list_rows"])

    overflow_html = ""
    if model["overflow_count"]:
        count = model["overflow_count"]
        overflow_html = (
            f'<div class="poster-overflow">+{count} more event{"s" if count != 1 else ""}</div>'
        )

    density = escape(model["density"])
    grid_cols = int(model["grid_columns"])
    logo_src = escape(model.get("logo_src", "/static/kd-logo.png"))

    if model["events_total"] == 0:
        body_html = (
            '<div class="poster-empty">'
            "<h3>No Events Today</h3>"
            "<p>Check back tomorrow!</p>"
            "</div>"
        )
    else:
        rows_part = f'<ul class="poster-rows">{rows_html}</ul>' if rows_html else ""
        body_html = (
            f'<div class="poster-grid">{cards_html}</div>'
            f"{rows_part}"
            f"{overflow_html}"
        )

    return (
        f'<section class="poster poster--{density} poster--cols-{grid_cols}" id="{escape(poster_id)}">'
        # Header
        '<header class="poster-header">'
        f'<div class="poster-logo-wrap"><img src="{logo_src}" alt="Kent Denver" class="poster-logo" /></div>'
        '<div class="poster-title-wrap">'
        f'<p class="poster-kicker">{escape(model["heading"])}</p>'
        f'<h1 class="poster-day-title">{escape(model["day_name"])}</h1>'
        f'<p class="poster-day-subtitle">{escape(model["day_long"])}</p>'
        "</div>"
        '<div class="poster-header-right">'
        f'<span class="poster-week-label">{escape(model["week_label"])}</span>'
        f'<span class="poster-slide-badge">SLIDE {model["slide_number"]}/{model["total_slides"]}</span>'
        "</div>"
        "</header>"
        # Red accent rule
        '<div class="poster-rule"></div>'
        # Body
        f'<div class="poster-body">{body_html}</div>'
        # Footer
        '<footer class="poster-footer">'
        "<span>@kentdenver</span>"
        "<span>Student Leadership Media</span>"
        "</footer>"
        "</section>"
    )


def poster_css() -> str:
    """Shared CSS for GUI preview and static export."""
    return """
:root {
  --kd-navy: #041E42;
  --kd-navy-mid: #0C3A6B;
  --kd-red: #A11919;
  --poster-bg: #E8EFF9;
  --card-bg: #FFFFFF;
  --text: #082544;
  --muted: #4B607A;
  --border: rgba(4,30,66,.11);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Red Hat Text', Arial, sans-serif; background: #b8c8de; }
.poster-shell { display: flex; justify-content: center; padding: 24px; }

/* ── Poster canvas ── */
.poster {
  width: 1080px;
  height: 1350px;
  display: flex;
  flex-direction: column;
  background: var(--poster-bg);
  overflow: hidden;
  position: relative;
  box-shadow: 0 32px 80px rgba(4,30,66,.4);
}

/* ── Header ── */
.poster-header {
  background: var(--kd-navy);
  padding: 26px 38px 24px;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}
/* Decorative soft circles in header */
.poster-header::before {
  content: '';
  position: absolute;
  right: -50px; top: -90px;
  width: 300px; height: 300px;
  border-radius: 50%;
  background: rgba(255,255,255,.05);
  pointer-events: none;
}
.poster-header::after {
  content: '';
  position: absolute;
  right: 110px; bottom: -60px;
  width: 200px; height: 200px;
  border-radius: 50%;
  background: rgba(255,255,255,.04);
  pointer-events: none;
}
.poster-logo-wrap {
  width: 68px; height: 68px;
  background: rgba(255,255,255,.13);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  padding: 7px;
  margin-top: 6px;
}
.poster-logo { width: 100%; height: auto; }
.poster-title-wrap { flex: 1; min-width: 0; }
.poster-kicker {
  font-size: 12px; font-weight: 800;
  letter-spacing: .18em; text-transform: uppercase;
  color: rgba(255,255,255,.48);
  margin-bottom: 3px;
}
.poster-day-title {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 96px; line-height: .88;
  letter-spacing: -.03em;
  color: #fff;
}
.poster-day-subtitle {
  font-size: 20px; font-weight: 600;
  color: rgba(255,255,255,.65);
  margin-top: 9px;
}
.poster-header-right {
  display: flex; flex-direction: column;
  align-items: flex-end; gap: 10px;
  flex-shrink: 0; padding-top: 2px;
}
.poster-week-label {
  font-size: 12px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase;
  color: rgba(255,255,255,.45);
  white-space: nowrap;
}
.poster-slide-badge {
  background: var(--kd-red);
  color: #fff;
  font-size: 12px; font-weight: 800;
  letter-spacing: .1em; text-transform: uppercase;
  padding: 5px 14px; border-radius: 4px;
  white-space: nowrap;
}

/* Red accent line under header */
.poster-rule {
  height: 5px;
  background: linear-gradient(90deg, var(--kd-red) 0%, #cc2929 30%, rgba(161,25,25,.2) 80%, transparent 100%);
  flex-shrink: 0;
}

/* ── Body ── */
.poster-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 18px 24px 14px;
  gap: 10px;
}

/* ── Cards grid ── */
.poster-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
  align-content: stretch;
}
.poster--cols-1 .poster-grid { grid-template-columns: 1fr; }
/* Last card spans full width when it's alone in its row */
.poster--cols-2 .poster-grid .poster-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

/* ── Event card ── */
.poster-card {
  background: var(--card-bg);
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 16px rgba(4,30,66,.1), 0 1px 4px rgba(4,30,66,.07);
}
.poster-card-top-bar { height: 10px; flex-shrink: 0; }
.poster-card-body {
  flex: 1;
  padding: 16px 18px 16px;
  display: flex;
  flex-direction: column;
}
.poster-card-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
}
.poster-badge {
  font-size: 11px; font-weight: 800;
  letter-spacing: .12em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 4px;
  background: rgba(4,30,66,.08);
  color: var(--kd-navy-mid);
  border-left: 3px solid var(--badge-accent, var(--kd-navy-mid));
  white-space: nowrap;
}
.poster-time {
  font-size: 17px; font-weight: 800;
  color: var(--muted); white-space: nowrap;
}
/* Main content area: flexes to fill space, centers title+subtitle vertically */
.poster-card-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 10px 0 8px;
}
.poster-card-title {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 44px; line-height: 1.0;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.poster-card-subtitle {
  font-size: 20px; font-weight: 700;
  color: var(--kd-navy-mid); line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-top: 8px;
}
/* Bottom section: always pinned to card bottom */
.poster-card-bottom { flex-shrink: 0; }
.poster-card-divider {
  height: 1px;
  background: var(--border);
  margin-bottom: 10px;
}
.poster-card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.poster-card-location {
  font-size: 14px; font-weight: 600;
  color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  min-width: 0;
}
.poster-card-category {
  font-size: 12px; font-weight: 800;
  letter-spacing: .1em; text-transform: uppercase;
  color: #8ba3c0;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── List rows ── */
.poster-rows {
  list-style: none;
  display: flex; flex-direction: column;
  gap: 7px;
  flex-shrink: 0;
}
.poster-row {
  display: grid;
  grid-template-columns: 88px 1fr auto;
  gap: 10px;
  align-items: center;
  background: rgba(255,255,255,.78);
  border-radius: 10px;
  padding: 10px 14px;
  border-left: 5px solid var(--row-accent, var(--kd-navy-mid));
}
.poster-row-time {
  font-size: 14px; font-weight: 800;
  color: var(--kd-navy-mid); white-space: nowrap;
}
.poster-row-main {
  font-size: 17px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.poster-row-main strong { color: var(--text); }
.poster-row-main em {
  font-style: normal; font-weight: 600;
  color: var(--muted); margin-left: 4px;
}
.poster-row-right {
  display: flex; flex-direction: column;
  align-items: flex-end; gap: 1px;
  flex-shrink: 0;
}
.poster-row-location {
  font-size: 13px; font-weight: 600;
  color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 200px;
}
.poster-row-cat {
  font-size: 11px; font-weight: 800;
  letter-spacing: .08em; text-transform: uppercase;
  color: #7a97b4;
}

/* ── Overflow count ── */
.poster-overflow {
  text-align: center;
  font-size: 14px; font-weight: 700;
  color: var(--muted);
  padding: 5px;
  flex-shrink: 0;
}

/* ── Empty state ── */
.poster-empty {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; gap: 14px;
}
.poster-empty h3 {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 60px; color: var(--text); opacity: .3;
}
.poster-empty p {
  font-size: 22px; color: var(--muted); opacity: .5;
}

/* ── Footer ── */
.poster-footer {
  background: var(--kd-navy);
  padding: 13px 38px;
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
}
.poster-footer span {
  color: rgba(255,255,255,.55);
  font-size: 14px; font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase;
}

/* ── Density: spacious (1 event) ── */
.poster--spacious .poster-day-title { font-size: 106px; }
.poster--spacious .poster-card-top-bar { height: 14px; }
.poster--spacious .poster-card-body { padding: 28px 32px 24px; }
.poster--spacious .poster-badge { font-size: 15px; padding: 7px 16px; }
.poster--spacious .poster-time { font-size: 30px; }
.poster--spacious .poster-card-main { padding: 24px 0 16px; }
.poster--spacious .poster-card-title { font-size: 90px; line-height: .95; -webkit-line-clamp: 4; }
.poster--spacious .poster-card-subtitle { font-size: 40px; margin-top: 18px; }
.poster--spacious .poster-card-divider { margin-bottom: 16px; }
.poster--spacious .poster-card-location { font-size: 24px; }
.poster--spacious .poster-card-category { font-size: 18px; }

/* ── Density: balanced (2–4 events) ── */
.poster--balanced .poster-card-top-bar { height: 11px; }
.poster--balanced .poster-card-body { padding: 18px 22px 20px; }
.poster--balanced .poster-badge { font-size: 13px; padding: 5px 12px; }
.poster--balanced .poster-time { font-size: 22px; }
.poster--balanced .poster-card-main { padding: 22px 0 14px; }
.poster--balanced .poster-card-title { font-size: 76px; line-height: .97; -webkit-line-clamp: 3; }
.poster--balanced .poster-card-subtitle { font-size: 32px; margin-top: 14px; -webkit-line-clamp: 2; }
.poster--balanced .poster-card-divider { margin-bottom: 14px; }
.poster--balanced .poster-card-location { font-size: 18px; }
.poster--balanced .poster-card-category { font-size: 14px; }

/* ── Density: compact (5–9 events) ── */
.poster--compact .poster-day-title { font-size: 82px; }
.poster--compact .poster-day-subtitle { font-size: 18px; }
.poster--compact .poster-header { padding: 22px 34px 20px; }
.poster--compact .poster-card-top-bar { height: 8px; }
.poster--compact .poster-card-body { padding: 11px 14px 12px; }
.poster--compact .poster-badge { font-size: 10px; padding: 3px 8px; }
.poster--compact .poster-time { font-size: 15px; }
.poster--compact .poster-card-main { padding: 8px 0 4px; }
.poster--compact .poster-card-title { font-size: 34px; }
.poster--compact .poster-card-subtitle { font-size: 18px; margin-top: 6px; }
.poster--compact .poster-card-divider { margin-bottom: 7px; }
.poster--compact .poster-card-location { font-size: 13px; }
.poster--compact .poster-card-category { font-size: 11px; }
.poster--compact .poster-row { padding: 9px 12px; }
.poster--compact .poster-row-main { font-size: 16px; }

/* ── Density: dense (10+ events) ── */
.poster--dense .poster-day-title { font-size: 72px; }
.poster--dense .poster-day-subtitle { font-size: 17px; }
.poster--dense .poster-header { padding: 18px 30px 16px; }
.poster--dense .poster-logo-wrap { width: 58px; height: 58px; }
.poster--dense .poster-body { padding: 12px 20px 10px; gap: 8px; }
.poster--dense .poster-grid { gap: 8px; }
.poster--dense .poster-card-top-bar { height: 6px; }
.poster--dense .poster-card-body { padding: 8px 12px 10px; }
.poster--dense .poster-badge { font-size: 9px; padding: 2px 7px; }
.poster--dense .poster-time { font-size: 13px; }
.poster--dense .poster-card-main { padding: 4px 0 2px; }
.poster--dense .poster-card-title { font-size: 24px; -webkit-line-clamp: 2; }
.poster--dense .poster-card-subtitle { font-size: 14px; margin-top: 3px; }
.poster--dense .poster-card-divider { margin-bottom: 5px; }
.poster--dense .poster-card-location { font-size: 12px; }
.poster--dense .poster-card-category { font-size: 10px; }
.poster--dense .poster-rows { gap: 5px; }
.poster--dense .poster-row { padding: 7px 10px; }
.poster--dense .poster-row-main { font-size: 15px; }
.poster--dense .poster-row-time { font-size: 12px; }
.poster--dense .poster-row-location { font-size: 11px; }
.poster--dense .poster-row-cat { font-size: 10px; }
"""


def render_carousel_document(slides: list[dict[str, Any]]) -> str:
    """Render all day slides into one HTML document."""
    slides_html = "".join(
        f'<article class="carousel-slide">{render_poster_fragment(slide, poster_id=f"instagram-poster-{idx}")}</article>'
        for idx, slide in enumerate(slides)
    )

    return (
        "<!DOCTYPE html>"
        "<html lang=\"en\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>Kent Denver Daily Carousel Posters</title>"
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@500;600;700&family=Red+Hat+Text:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">"
        f"<style>{poster_css()} .carousel-doc{{display:flex;flex-direction:column;gap:24px;align-items:center;padding:20px;}} .carousel-slide{{max-width:1080px;}}</style>"
        "</head><body><main class=\"carousel-doc\">"
        f"{slides_html}"
        "</main></body></html>"
    )


def _load_custom_events(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Custom events file must contain a JSON list")
    return payload


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily Kent Denver Instagram carousel posters")
    parser.add_argument("--this-week", action="store_true", help="Use current week (Mon-Sun)")
    parser.add_argument("--next-week", action="store_true", help="Use next week (Mon-Sun)")
    parser.add_argument("--start-date", type=str, help="Custom start date YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="Custom end date YYYY-MM-DD")
    parser.add_argument("--custom-events", type=str, help="Path to JSON list of custom events")
    parser.add_argument("--heading", type=str, default="This Week at Kent Denver", help="Poster heading")
    parser.add_argument("--output-html", type=str, default=str(ROOT_DIR / "instagram-poster" / "carousel.html"))
    return parser.parse_args()


def main() -> None:
    args = _args()

    if args.start_date and args.end_date:
        start, end = get_week_bounds(start_date=args.start_date, end_date=args.end_date)
    else:
        mode = "this" if args.this_week else "next"
        start, end = get_week_bounds(mode=mode)

    events = fetch_week_events(start, end)
    custom_events = _load_custom_events(args.custom_events)
    merged = merge_events(events, custom_events)
    slides = build_daily_carousel_models(merged, start, end, heading=args.heading, logo_src=KDS_LOGO_WEB_URL)
    html = render_carousel_document(slides)

    output = Path(args.output_html)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    print(f"Generated carousel HTML: {output}")
    print(f"Date range: {start} to {end}")
    print(f"Slides: {len(slides)} | Source events: {len(events)} | Custom events: {len(custom_events)} | Total events: {len(merged)}")


if __name__ == "__main__":
    main()
