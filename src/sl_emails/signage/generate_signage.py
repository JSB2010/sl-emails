#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime
from html import escape
import re
import sys
from typing import Dict, List

from sl_emails.config import SIGNAGE_OUTPUT_HTML
from sl_emails.domain.dates import iso_to_date
from sl_emails.domain.email_presets import (
    ARTS_CONFIG,
    DEFAULT_ARTS_CONFIG,
    DEFAULT_SCHOOL_EVENT_CONFIG,
    DEFAULT_SPORT_CONFIG,
    SCHOOL_EVENT_CONFIG,
    SPORT_CONFIG,
)
from sl_emails.ingest.generate_games import KDS_PRIMARY_LOGO_URL, build_icon_html
from sl_emails.services.event_shapes import PosterEvent
from sl_emails.services.signage_ingest import fetch_signage_events

SCREEN_STYLES = """
:root {
    --surface: #edf2f9;
    --panel: rgba(255, 255, 255, 0.94);
    --panel-strong: #ffffff;
    --ink: #0d1f36;
    --muted: #52697f;
    --border: rgba(4, 30, 66, 0.11);
    --brand: #041e42;
    --brand-mid: #0c3a6b;
    --brand-soft: #165191;
    --brand-red: #a11919;
    --brand-gold: #c49000;
    --success: #12825a;
    --shadow: 0 30px 80px rgba(4, 30, 66, 0.16);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    width: 2500px;
    height: 1650px;
    overflow: hidden;
    font-family: "Red Hat Text", Arial, sans-serif;
    color: var(--ink);
    background:
        radial-gradient(circle at top left, rgba(196, 144, 0, 0.16), transparent 26%),
        radial-gradient(circle at bottom right, rgba(12, 58, 107, 0.14), transparent 28%),
        linear-gradient(180deg, #f4f7fb 0%, #e6edf7 100%);
}

body::before,
body::after {
    content: "";
    position: fixed;
    border-radius: 999px;
    filter: blur(8px);
    pointer-events: none;
    opacity: 0.8;
}

body::before {
    width: 420px;
    height: 420px;
    top: -120px;
    right: 180px;
    background: rgba(161, 25, 25, 0.08);
}

body::after {
    width: 520px;
    height: 520px;
    bottom: -180px;
    left: -120px;
    background: rgba(196, 144, 0, 0.08);
}

.screen {
    position: relative;
    height: 100%;
    padding: 38px 42px 30px;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.screen-header {
    display: grid;
    grid-template-columns: minmax(980px, 1.15fr) minmax(760px, 1fr);
    align-items: stretch;
    gap: 26px;
    padding: 28px 32px;
    border-radius: 34px;
    background: linear-gradient(135deg, rgba(4, 30, 66, 0.98) 0%, rgba(12, 58, 107, 0.97) 100%);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: 0 16px 48px rgba(4, 30, 66, 0.28);
}

.screen-header__brand {
    display: flex;
    align-items: center;
    gap: 22px;
    min-width: 0;
}

.screen-header__logo-wrap {
    width: 112px;
    height: 112px;
    border-radius: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.09);
    border: 1px solid rgba(255, 255, 255, 0.13);
    flex-shrink: 0;
}

.screen-header__logo {
    width: 90px;
    height: auto;
}

.screen-header__eyebrow {
    display: block;
    margin-bottom: 10px;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.72);
}

.screen-header__title {
    font-family: "Crimson Pro", Georgia, serif;
    font-size: 96px;
    font-weight: 700;
    line-height: 0.95;
    letter-spacing: -0.03em;
}

.screen-header__date {
    margin-top: 10px;
    font-size: 38px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.88);
}

.screen-header__stats {
    align-self: stretch;
    display: grid;
    grid-template-columns: repeat(var(--stats-columns, 3), minmax(0, 1fr));
    gap: 14px;
}

.summary-pill {
    min-width: 0;
    padding: 18px 22px;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(8px);
    min-height: 98px;
}

.summary-pill__label {
    display: block;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.7);
}

.summary-pill__value {
    display: block;
    margin-top: 8px;
    font-family: "Crimson Pro", Georgia, serif;
    font-size: 50px;
    line-height: 1;
    color: #ffffff;
}

.screen-main {
    flex: 1;
    min-height: 0;
    display: flex;
}

.screen[data-density="compact"] .screen-header {
    grid-template-columns: minmax(940px, 1.08fr) minmax(720px, 1fr);
    padding: 26px 30px;
}

.screen[data-density="compact"] .screen-header__title {
    font-size: 90px;
}

.screen[data-density="compact"] .summary-pill {
    padding: 16px 18px;
    min-height: 92px;
}

.screen[data-density="compact"] .summary-pill__label {
    font-size: 16px;
}

.screen[data-density="compact"] .summary-pill__value {
    font-size: 46px;
}

.screen[data-density="dense"] {
    gap: 16px;
}

.screen[data-density="dense"] .screen-header {
    grid-template-columns: minmax(900px, 1.02fr) minmax(720px, 1fr);
    gap: 22px;
    padding: 24px 28px;
}

.screen[data-density="dense"] .screen-header__logo-wrap {
    width: 104px;
    height: 104px;
}

.screen[data-density="dense"] .screen-header__logo {
    width: 84px;
}

.screen[data-density="dense"] .screen-header__eyebrow {
    margin-bottom: 8px;
    font-size: 20px;
}

.screen[data-density="dense"] .screen-header__title {
    font-size: 84px;
}

.screen[data-density="dense"] .screen-header__date {
    margin-top: 10px;
    font-size: 34px;
}

.screen[data-density="dense"] .summary-pill {
    padding: 15px 18px;
    min-height: 88px;
}

.screen[data-density="dense"] .summary-pill__label {
    font-size: 15px;
}

.screen[data-density="dense"] .summary-pill__value {
    font-size: 44px;
}

.stage {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 22px;
    border-radius: 34px;
    background: var(--panel);
    border: 1px solid rgba(255, 255, 255, 0.7);
    box-shadow: var(--shadow);
    backdrop-filter: blur(14px);
}

.screen[data-density="compact"] .stage {
    padding: 24px;
}

.screen[data-density="dense"] .stage {
    gap: 16px;
    padding: 20px;
}

.board-layout {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.screen[data-density="dense"] .board-layout {
    gap: 12px;
}

.board-row {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(var(--row-columns, 1), minmax(0, 1fr));
    gap: 16px;
}

.screen[data-density="dense"] .board-row {
    gap: 12px;
}

.board-row > .event-card {
    height: 100%;
}

.event-card {
    position: relative;
    display: flex;
    min-height: 0;
    overflow: hidden;
    border-radius: 30px;
    border: 1px solid var(--accent-soft);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 255, 0.98) 100%);
    box-shadow: 0 16px 34px rgba(4, 30, 66, 0.08);
}

.event-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 14px;
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-deep) 100%);
}

.event-card::after {
    content: "";
    position: absolute;
    width: 240px;
    height: 240px;
    top: -80px;
    right: -60px;
    border-radius: 999px;
    background: var(--accent-cloud);
}

.event-card__content {
    position: relative;
    z-index: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px 24px 22px 32px;
}

.event-card__top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
}

.event-card__chips,
.event-card__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.event-chip,
.event-meta-pill {
    display: inline-flex;
    align-items: center;
    min-height: 34px;
    padding: 7px 14px;
    border-radius: 999px;
    font-size: 16px;
    font-weight: 700;
}

.event-chip--category {
    background: var(--accent-cloud);
    color: var(--accent-deep);
}

.event-chip--badge {
    background: var(--badge-bg);
    color: var(--badge-ink);
}

.event-card__icon {
    width: 82px;
    height: 82px;
    min-width: 82px;
    border-radius: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, rgba(255, 255, 255, 0.92) 0%, var(--accent-cloud) 100%);
    border: 1px solid var(--accent-soft);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.event-card__copy {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.event-card__title {
    font-family: "Crimson Pro", Georgia, serif;
    font-size: 62px;
    font-weight: 700;
    line-height: 0.98;
    letter-spacing: -0.025em;
}

.event-card__summary {
    color: var(--brand-mid);
    font-size: 35px;
    font-weight: 700;
    line-height: 1.24;
}

.event-card__detail {
    color: var(--muted);
    font-size: 30px;
    line-height: 1.38;
}

.event-card__footer {
    margin-top: auto;
    display: flex;
    align-items: flex-end;
    justify-content: flex-end;
    gap: 14px;
}

.event-meta-pill {
    background: rgba(4, 30, 66, 0.05);
    color: var(--ink);
    border: 1px solid rgba(4, 30, 66, 0.08);
}

.event-card__time {
    min-width: 240px;
    padding: 16px 18px;
    border-radius: 22px;
    background: rgba(4, 30, 66, 0.04);
    border: 1px solid rgba(4, 30, 66, 0.08);
    text-align: right;
}

.event-card__time-label {
    display: block;
    color: #708095;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.event-card__time-value {
    display: block;
    margin-top: 6px;
    color: var(--brand);
    font-size: 46px;
    font-weight: 800;
    line-height: 1;
}

.event-card[data-density="spotlight"] .event-card__content {
    padding: 40px 40px 36px 52px;
    gap: 24px;
}

.event-card[data-density="spotlight"] .event-card__icon {
    width: 108px;
    height: 108px;
    min-width: 108px;
    border-radius: 28px;
}

.event-card[data-density="spotlight"] .event-card__title {
    font-size: 88px;
}

.event-card[data-density="spotlight"] .event-card__summary {
    font-size: 46px;
}

.event-card[data-density="spotlight"] .event-card__detail {
    font-size: 34px;
}

.event-card[data-density="spotlight"] .event-card__time {
    min-width: 280px;
    padding: 20px 24px;
}

.event-card[data-density="spotlight"] .event-card__time-value {
    font-size: 56px;
}

.event-card[data-density="compact"] .event-card__content {
    padding: 22px 22px 20px 30px;
}

.event-card[data-density="compact"] .event-card__icon {
    width: 76px;
    height: 76px;
    min-width: 76px;
}

.event-card[data-density="compact"] .event-card__title {
    font-size: 58px;
}

.event-card[data-density="compact"] .event-card__summary {
    font-size: 34px;
}

.event-card[data-density="compact"] .event-card__detail {
    font-size: 28px;
}

.event-card[data-density="compact"] .event-card__time {
    min-width: 214px;
}

.event-card[data-density="compact"] .event-card__time-value {
    font-size: 42px;
}

.event-card[data-density="compact"] .event-card__chips,
.event-card[data-density="dense"] .event-card__chips {
    gap: 8px;
}

.event-card[data-density="dense"] .event-card__content {
    padding: 18px 18px 16px 26px;
    gap: 12px;
}

.event-card[data-density="dense"]::before {
    width: 11px;
}

.event-card[data-density="dense"] .event-card__icon {
    width: 64px;
    height: 64px;
    min-width: 64px;
    border-radius: 18px;
}

.event-card[data-density="dense"] .event-card__title {
    font-size: 50px;
}

.event-card[data-density="dense"] .event-card__summary {
    font-size: 31px;
}

.event-card[data-density="dense"] .event-card__detail {
    font-size: 26px;
}

.event-card[data-density="dense"] .event-chip,
.event-card[data-density="dense"] .event-meta-pill {
    min-height: 34px;
    padding: 8px 14px;
    font-size: 17px;
}

.event-card[data-density="dense"] .event-card__time {
    min-width: 180px;
    padding: 14px 16px;
}

.event-card[data-density="dense"] .event-card__time-value {
    font-size: 40px;
}

.event-card[data-density="dense"] .event-card__time-label {
    font-size: 15px;
}

.empty-state {
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

.empty-state__card {
    width: min(1240px, 100%);
    padding: 64px 72px;
    border-radius: 34px;
    border: 1px solid rgba(4, 30, 66, 0.12);
    background: linear-gradient(165deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 255, 0.98) 100%);
    box-shadow: 0 24px 60px rgba(4, 30, 66, 0.16);
    text-align: center;
}

.empty-state__icon {
    width: 132px;
    height: 132px;
    margin: 0 auto 28px;
    border-radius: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(4, 30, 66, 0.06);
    color: var(--brand);
    font-size: 68px;
}

.empty-state__title {
    font-family: "Crimson Pro", Georgia, serif;
    font-size: 80px;
    line-height: 0.98;
}

.empty-state__copy {
    margin-top: 18px;
    color: var(--muted);
    font-size: 34px;
    line-height: 1.4;
}

.screen-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 18px;
    padding: 0 8px;
    color: #55697f;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
"""

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

def get_date_range(date_str=None):
    """Get date in the format needed for fetching

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If None, uses today.
    """
    if date_str:
        # Validate and use provided date
        try:
            target_day = iso_to_date(date_str)
        except ValueError:
            print(f"❌ Invalid date format: {date_str}")
            print("   Please use YYYY-MM-DD format (e.g., 2025-11-08)")
            sys.exit(1)
    else:
        target_day = datetime.now().date()

    day_id = target_day.isoformat()
    return day_id, day_id, target_day

def fetch_events_for_date(date_str=None):
    """Fetch all games and events for the specified date

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If None, uses today.
    """
    start_date, _end_date, target_day = get_date_range(date_str)

    print(f"🔍 Fetching events for {start_date} ({target_day.strftime('%A, %B %d, %Y')})...")

    all_events = fetch_signage_events(start_date)
    games = [event for event in all_events if event.source == "athletics"]
    arts_events = [event for event in all_events if event.source == "arts"]
    print(f"✅ Found {len(games)} sports games")
    print(f"✅ Found {len(arts_events)} arts events")
    print(f"📊 Total: {len(all_events)} events")

    return all_events, target_day

def categorize_events(events: List[PosterEvent]):
    """Categorize events into featured and regular."""
    featured = []
    regular = []

    for event in events:
        if event.priority >= 4 or event.source == "arts":
            featured.append(event)
        elif event.source == "athletics":
            if "varsity" in (event.team or "").lower():
                featured.append(event)
            else:
                regular.append(event)
        else:
            regular.append(event)

    return featured, regular


def source_counts(events: List[PosterEvent]) -> Dict[str, int]:
    counts = {"athletics": 0, "arts": 0, "custom": 0}
    for event in events:
        counts[event.source if event.source in counts else "custom"] += 1
    counts["total"] = len(events)
    return counts


def normalized_hex(color: str | None, fallback: str = "#041E42") -> str:
    value = str(color or "").strip()
    if HEX_COLOR_RE.fullmatch(value):
        return value.upper()
    return fallback


def hex_to_rgba(color: str | None, alpha: float, fallback: str = "#041E42") -> str:
    value = normalized_hex(color, fallback).lstrip("#")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha:.3f})"


def audience_label(audiences: list[str]) -> str:
    normalized = {str(audience or "").strip().lower() for audience in audiences if str(audience or "").strip()}
    if {"middle-school", "upper-school"}.issubset(normalized):
        return "All School"
    if "middle-school" in normalized:
        return "Middle School"
    if "upper-school" in normalized:
        return "Upper School"
    return ""


def source_label(event: PosterEvent) -> str:
    if event.source == "athletics":
        return "Athletics"
    if event.source == "arts":
        return "Arts"
    return "School Event"


def event_title(event: PosterEvent) -> str:
    if event.source == "athletics":
        return event.team or event.title or "Team Event"
    return event.title or "Untitled Event"


def event_summary(event: PosterEvent) -> str:
    if event.source == "athletics":
        if event.opponent:
            return f"vs. {event.opponent}"
        if event.subtitle:
            return event.subtitle
        return "Opponent TBA"
    if event.subtitle:
        return event.subtitle
    return event.category or "School Event"


def event_detail(event: PosterEvent) -> str:
    if event.source == "athletics":
        return event.location or "Location TBA"
    return event.location or "On Campus"


def summary_pills_html(events: List[PosterEvent]) -> str:
    counts = source_counts(events)
    pills: list[str] = [
        f"""
        <div class="summary-pill">
          <span class="summary-pill__label">Total Events</span>
          <span class="summary-pill__value">{counts['total']}</span>
        </div>
        """,
    ]
    if counts["athletics"]:
        pills.append(
            f"""
            <div class="summary-pill">
              <span class="summary-pill__label">Athletics</span>
              <span class="summary-pill__value">{counts['athletics']}</span>
            </div>
            """
        )
    if counts["arts"]:
        pills.append(
            f"""
            <div class="summary-pill">
              <span class="summary-pill__label">Arts</span>
              <span class="summary-pill__value">{counts['arts']}</span>
            </div>
            """
        )
    if counts["custom"]:
        pills.append(
            f"""
            <div class="summary-pill">
              <span class="summary-pill__label">School Events</span>
              <span class="summary-pill__value">{counts['custom']}</span>
            </div>
            """
        )
    return "".join(pills)


def layout_plan(total_events: int) -> dict[str, object]:
    if total_events <= 1:
        return {"rows": [1], "density": "spotlight"}
    if total_events == 2:
        return {"rows": [2], "density": "spotlight"}
    if total_events == 3:
        return {"rows": [3], "density": "cozy"}
    if total_events == 4:
        return {"rows": [2, 2], "density": "cozy"}
    if total_events == 5:
        return {"rows": [3, 2], "density": "compact"}
    if total_events == 6:
        return {"rows": [3, 3], "density": "compact"}
    if total_events == 7:
        return {"rows": [4, 3], "density": "dense"}
    if total_events == 8:
        return {"rows": [4, 4], "density": "dense"}
    if total_events == 9:
        return {"rows": [3, 3, 3], "density": "dense"}
    if total_events == 10:
        return {"rows": [5, 5], "density": "dense"}

    rows: list[int] = []
    remaining = total_events
    while remaining > 0:
        chunk = 5 if remaining >= 5 else remaining
        rows.append(chunk)
        remaining -= chunk
    return {"rows": rows, "density": "dense"}


def event_card_html(event: PosterEvent, *, density: str) -> str:
    config = event_display_config(event)
    accent_color = normalized_hex(event.accent or config.get("accent_color") or config.get("border_color"))
    badge = event_badge_style(event)
    title = escape(event_title(event))
    summary = escape(event_summary(event))
    detail = escape(event_detail(event))
    category = escape(event.category or source_label(event))
    icon_size = {"spotlight": 66, "cozy": 54, "compact": 46, "dense": 36}.get(density, 46)
    icon_html = build_icon_html(config.get("icon"), f"{event.category or event.title} icon", size=icon_size)
    category_chip = f'<span class="event-chip event-chip--category">{category}</span>'
    badge_chip = (
        f'<span class="event-chip event-chip--badge">{escape(badge["text"])}</span>'
        if event.source == "athletics"
        else ""
    )
    audience = audience_label(event.audiences)
    meta_pills: list[str] = []
    if audience and audience != "All School":
        meta_pills.append(f'<span class="event-meta-pill">{escape(audience)}</span>')
    meta_html = "".join(meta_pills)
    footer_meta_html = f'<div class="event-card__meta">{meta_html}</div>' if meta_html else ""

    return f"""
    <article
      class="event-card"
      data-density="{density}"
      style="--accent: {accent_color}; --accent-deep: {normalized_hex(config.get('border_color') or accent_color)}; --accent-soft: {hex_to_rgba(accent_color, 0.20)}; --accent-cloud: {hex_to_rgba(accent_color, 0.10)}; --badge-bg: {badge['background']}; --badge-ink: {badge['color']};"
    >
      <div class="event-card__content">
        <div class="event-card__top">
          <div class="event-card__chips">
            {category_chip}
            {badge_chip}
          </div>
          <div class="event-card__icon">{icon_html}</div>
        </div>

        <div class="event-card__copy">
          <h2 class="event-card__title">{title}</h2>
          <p class="event-card__summary">{summary}</p>
          <p class="event-card__detail">{detail}</p>
        </div>

        <div class="event-card__footer">
          {footer_meta_html}
          <div class="event-card__time">
            <span class="event-card__time-label">Start</span>
            <span class="event-card__time-value">{escape(event.time or "TBA")}</span>
          </div>
        </div>
      </div>
    </article>
    """


def empty_state_html() -> str:
    return """
    <section class="empty-state">
      <div class="empty-state__card">
        <div class="empty-state__icon">📅</div>
        <h2 class="empty-state__title">No Events Today</h2>
        <p class="empty-state__copy">The daily board is clear for now. Check back tomorrow for the latest games, performances, and campus events.</p>
      </div>
    </section>
    """


def events_layout_html(events: List[PosterEvent]) -> str:
    if not events:
        return empty_state_html()

    featured, regular = categorize_events(events)
    ordered_events = featured + regular
    plan = layout_plan(len(ordered_events))
    rows = list(plan["rows"])
    density = str(plan["density"])

    parts = ['<section class="board-layout">']
    cursor = 0
    for row_columns in rows:
        row_events = ordered_events[cursor:cursor + row_columns]
        cursor += row_columns
        cards = "".join(event_card_html(event, density=density) for event in row_events)
        parts.append(
            f"""
            <div class="board-row" style="--row-columns: {row_columns};">
              {cards}
            </div>
            """
        )

    parts.append("</section>")
    return "".join(parts)

def event_display_config(event: PosterEvent) -> Dict[str, str]:
    event_key = (event.category or event.title or "").lower()
    if event.source == "athletics":
        team_key = (event.team or event.title or "").lower()
        for sport_key, config in SPORT_CONFIG.items():
            if sport_key in team_key or sport_key in event_key:
                return dict(config)
        return dict(DEFAULT_SPORT_CONFIG)

    for category_key, config in ARTS_CONFIG.items():
        if category_key in event_key:
            return dict(config)
    for category_key, config in SCHOOL_EVENT_CONFIG.items():
        if category_key in event_key:
            return dict(config)
    return dict(DEFAULT_ARTS_CONFIG if event.source == "arts" else DEFAULT_SCHOOL_EVENT_CONFIG)


def event_badge_style(event: PosterEvent) -> Dict[str, str]:
    badge = (event.badge or "").strip().upper()
    if event.source == "athletics":
        if badge == "AWAY" or not event.is_home:
            return {
                "background": "#fef3c7",
                "color": "#92400e",
                "text": "Away",
            }
        return {
            "background": "#dcfce7",
            "color": "#166534",
            "text": "Home",
        }
    return {
        "background": "#e0e7ff",
        "color": "#3730a3",
        "text": "Event",
    }

def _coerce_display_date(target_date: date | datetime | str | None) -> datetime:
    if target_date is None:
        return datetime.now()
    if isinstance(target_date, str):
        return datetime.combine(iso_to_date(target_date), datetime.min.time())
    if isinstance(target_date, datetime):
        return target_date
    return datetime.combine(target_date, datetime.min.time())


def generate_signage_html(events: List[PosterEvent], target_date: date | datetime | str | None = None) -> str:
    """Generate the complete HTML for digital signage

    Args:
        events: List of games and events to display
        target_date: The date to display. If None, uses current date.
    """
    target_date = _coerce_display_date(target_date)
    date_display = target_date.strftime("%A, %B %d, %Y")

    logo_url = KDS_PRIMARY_LOGO_URL
    board_density = str(layout_plan(len(events)).get("density", "dense")) if events else "spotlight"
    content_html = events_layout_html(events)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kent Denver Events - {date_display}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@500;600;700&family=Red+Hat+Text:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        {SCREEN_STYLES}
    </style>
</head>
<body>
    <div class="screen" data-density="{board_density}">
        <header class="screen-header">
            <div class="screen-header__brand">
                <div class="screen-header__logo-wrap">
                    <img src="{logo_url}" alt="Kent Denver" class="screen-header__logo">
                </div>
                <div>
                    <span class="screen-header__eyebrow">Kent Denver Digital Signage</span>
                    <h1 class="screen-header__title">Today's Events</h1>
                    <div class="screen-header__date">{date_display}</div>
                </div>
            </div>
            <div class="screen-header__stats">
                {summary_pills_html(events)}
            </div>
        </header>

        <main class="screen-main">
            <section class="stage">
                {content_html}
            </section>
        </main>

        <footer class="screen-footer">
            <span>Kent Denver Student Leadership Media</span>
        </footer>
    </div>
</body>
</html>"""

    return html

def main():
    """Main function to generate digital signage"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Generate Kent Denver digital signage HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  PYTHONPATH=src python3 -m sl_emails.signage.generate_signage
  PYTHONPATH=src python3 -m sl_emails.signage.generate_signage --date 2025-11-08
        '''
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Date to generate signage for (YYYY-MM-DD format). Defaults to today.',
        metavar='YYYY-MM-DD'
    )

    args = parser.parse_args()

    print("🖥️  Kent Denver Digital Signage Generator")
    print("=" * 50)

    # Fetch events for the specified date
    events, target_date = fetch_events_for_date(args.date)

    # Generate HTML
    print("\n📝 Generating HTML...")
    html = generate_signage_html(events, target_date)

    # Save to the supported signage artifact path.
    output_path = SIGNAGE_OUTPUT_HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Digital signage generated: {output_path}")
    print(f"📊 Displayed {len(events)} event(s)")
    print("\n🎉 Generation complete!")

if __name__ == '__main__':
    main()
