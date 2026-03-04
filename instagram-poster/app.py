#!/usr/bin/env python3
"""Local web app for generating Kent Denver daily carousel posters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from poster_generator import (
    build_daily_carousel_models,
    fetch_week_events,
    get_week_bounds,
    merge_events,
    normalize_custom_event,
    poster_css,
    poster_event_from_dict,
    render_poster_fragment,
)

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))


@app.get("/")
def index():
    today = datetime.now().date()
    start, end = get_week_bounds(mode="next", today=today)
    slides = build_daily_carousel_models([], start, end)

    return render_template(
        "index.html",
        default_start=start.isoformat(),
        default_end=end.isoformat(),
        default_mode="next",
        poster_css=poster_css(),
        initial_poster_html=render_poster_fragment(slides[0], poster_id="instagram-poster-0"),
        initial_slide_count=len(slides),
    )


@app.post("/api/fetch-events")
def fetch_events() -> Any:
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode", "next"))
    start_value = payload.get("start_date")
    end_value = payload.get("end_date")

    try:
        if start_value and end_value:
            start, end = get_week_bounds(start_date=str(start_value), end_date=str(end_value))
        else:
            start, end = get_week_bounds(mode=mode)

        events = fetch_week_events(start, end)
        return jsonify(
            {
                "ok": True,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "events": [event.to_dict() for event in events],
                "message": f"Fetched {len(events)} events.",
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/render")
def render() -> Any:
    payload = request.get_json(silent=True) or {}

    start_raw = str(payload.get("start_date", "")).strip()
    end_raw = str(payload.get("end_date", "")).strip()
    heading = str(payload.get("heading", "This Week at Kent Denver")).strip() or "This Week at Kent Denver"

    base_payload = payload.get("base_events", [])
    custom_payload = payload.get("custom_events", [])

    try:
        start, end = get_week_bounds(start_date=start_raw, end_date=end_raw)

        base_events = [poster_event_from_dict(item) for item in base_payload if isinstance(item, dict)]
        valid_custom: list[dict[str, Any]] = []
        invalid_custom: list[dict[str, str]] = []

        for idx, custom in enumerate(custom_payload):
            if not isinstance(custom, dict):
                invalid_custom.append({"index": str(idx), "error": "Custom event must be an object."})
                continue
            try:
                normalize_custom_event(custom)
                valid_custom.append(custom)
            except Exception as exc:  # noqa: BLE001
                invalid_custom.append({"index": str(idx), "error": str(exc)})

        merged = merge_events(base_events, valid_custom)
        models = build_daily_carousel_models(merged, start, end, heading=heading)

        slides = []
        first_non_empty: int | None = None
        for idx, model in enumerate(models):
            if model["events_total"] > 0 and first_non_empty is None:
                first_non_empty = idx
            slides.append(
                {
                    "index": idx,
                    "date": model["date_iso"],
                    "day": model["day_name"],
                    "events_total": model["events_total"],
                    "overflow_count": model["overflow_count"],
                    "poster_html": render_poster_fragment(model, poster_id=f"instagram-poster-{idx}"),
                }
            )

        if first_non_empty is None:
            first_non_empty = 0

        return jsonify(
            {
                "ok": True,
                "slides": slides,
                "slide_count": len(slides),
                "current_index": first_non_empty,
                "invalid_custom": invalid_custom,
                "normalized_events": [event.to_dict() for event in merged],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5050)
