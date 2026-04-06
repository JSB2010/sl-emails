from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import sys
from zoneinfo import ZoneInfo


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_in_timezone(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def iso_to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def week_start_for(value: str) -> str:
    parsed = iso_to_date(value)
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def week_end_for(start_date: str) -> str:
    return (iso_to_date(week_start_for(start_date)) + timedelta(days=6)).isoformat()


def default_send_date_for_week(week_start: str) -> str:
    return (iso_to_date(week_start_for(week_start)) - timedelta(days=1)).isoformat()


def resolve_week_bounds(
    mode: str = "next",
    *,
    today: date | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[date, date]:
    if start_date and end_date:
        start = iso_to_date(week_start_for(start_date))
        end = iso_to_date(end_date)
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        return start, end

    today = today or datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    if mode == "next":
        monday = monday + timedelta(days=7)
    elif mode != "this":
        raise ValueError("mode must be 'this' or 'next'")
    return monday, monday + timedelta(days=6)


def event_date_for_sort(value: str) -> date:
    text = (value or "").strip()
    if not text:
        return date.max
    for fmt in ("%Y-%m-%d", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return date.max


def normalize_to_iso_date(value: str) -> str:
    parsed = event_date_for_sort(value)
    return value if parsed == date.max else parsed.isoformat()


def time_for_sort(value: str) -> time:
    normalized = (value or "").strip().upper().replace(".", "")
    if not normalized or normalized in {"TBA", "ALL DAY"}:
        return time(23, 59)
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue
    return time(23, 59)


def time_sort_key(value: str) -> tuple[int, str]:
    text = (value or "").strip()
    if not text or text.upper() == "TBA":
        return (99_999, text)

    normalized = text.replace(".", "")
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return (parsed.hour * 60 + parsed.minute, text)
        except ValueError:
            continue
    return (99_998, text)


def overlap_dates(start_date: str, end_date: str, week_start: str, week_end: str) -> list[date]:
    start = max(iso_to_date(start_date), iso_to_date(week_start))
    end = min(iso_to_date(end_date), iso_to_date(week_end))
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def display_date(value: date) -> str:
    return value.strftime("%b %d %Y")


def format_email_date_range(start_date: str, end_date: str) -> str:
    start = iso_to_date(start_date)
    end = iso_to_date(end_date)
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%B')} {start.day}–{end.day}, {start.year}"
    if start.year == end.year:
        return f"{start.strftime('%B %d')}–{end.strftime('%B %d')}, {start.year}"
    return f"{start.strftime('%B %d, %Y')}–{end.strftime('%B %d, %Y')}"


def format_poster_week_label(start: date, end: date) -> str:
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%B')} {start.day}-{end.day}, {start.year}"
    if start.year == end.year:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"


def format_day_long(value: date) -> str:
    return value.strftime("%A, %B %-d") if sys.platform != "win32" else value.strftime("%A, %B %d").replace(" 0", " ")
