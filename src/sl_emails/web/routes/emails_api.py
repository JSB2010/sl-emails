"""Weekly email API routes preserved under the dedicated web package."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from flask import Blueprint, jsonify, request

from sl_emails.domain.dates import utc_now_iso
from sl_emails.domain.weekly import DEFAULT_HEADING
from sl_emails.ingest import generate_games
from sl_emails.services.event_shapes import source_event_to_weekly_event_payload
from sl_emails.services.weekly_outputs import build_weekly_email_outputs as render_weekly_email_outputs

from ..support import get_emails_store, json_error, open_emails_access


blueprint = Blueprint("emails_api", __name__, url_prefix="/api/emails")


def build_weekly_email_outputs(week: Any) -> dict[str, dict[str, Any]]:
    return render_weekly_email_outputs(week, generate_games_module=generate_games)


@blueprint.get("/weeks/<week_id>")
@open_emails_access
def get_week(week_id: str) -> Any:
    week = get_emails_store().get_week(week_id)
    if week is None:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.put("/weeks/<week_id>")
@open_emails_access
def save_week(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        week = get_emails_store().save_week(week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.post("/weeks/<week_id>/events")
@open_emails_access
def create_custom_event(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        week = get_emails_store().add_event(week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "event": week.events[-1].to_dict() if week.events else None}), 201


@blueprint.post("/weeks/<week_id>/preview")
@open_emails_access
def preview_week(week_id: str) -> Any:
    week = get_emails_store().get_week(week_id)
    if week is None:
        return json_error(f"No weekly draft found for {week_id}", status=404)

    try:
        outputs = build_weekly_email_outputs(week)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.post("/weeks/<week_id>/approve")
@open_emails_access
def approve_week(week_id: str) -> Any:
    actor = str(request.headers.get("X-Email-Actor", "open-access")).strip() or "open-access"
    try:
        week = get_emails_store().approve_week(week_id, approved_by=actor)
        outputs = build_weekly_email_outputs(week)
    except KeyError:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.post("/weeks/<week_id>/sent")
@open_emails_access
def mark_week_sent(week_id: str) -> Any:
    actor = str(request.headers.get("X-Email-Actor", "open-access")).strip() or "open-access"
    payload = request.get_json(silent=True) or {}
    requested_state = str(payload.get("state") or "sent").strip().lower() or "sent"
    if requested_state not in {"sending", "sent", "unsent"}:
        return json_error("state must be one of: sending, sent, unsent", status=400)

    try:
        if requested_state == "sending":
            week = get_emails_store().claim_week_send(week_id, sending_by=actor)
        elif requested_state == "unsent":
            week = get_emails_store().reset_week_send(week_id)
        else:
            week = get_emails_store().mark_week_sent(week_id, sent_by=actor)
    except KeyError:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    except ValueError as exc:
        return json_error(str(exc), status=409)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "sent": week.sent})


@blueprint.get("/weeks")
@open_emails_access
def list_weeks() -> Any:
    try:
        week_ids = get_emails_store().list_weeks()
    except RuntimeError as exc:
        return json_error(str(exc), status=503)
    return jsonify({"ok": True, "weeks": week_ids})


@blueprint.post("/weeks/<week_id>/ingest")
@open_emails_access
def ingest_week(week_id: str) -> Any:
    """Scrape fresh events from source and replace the week draft in Firestore."""
    try:
        start = date.fromisoformat(week_id)
    except ValueError:
        return json_error("week_id must be a valid ISO date (YYYY-MM-DD)", status=400)

    end = start + timedelta(days=6)
    end_date_str = end.isoformat()

    try:
        existing = get_emails_store().get_week(week_id)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)
    if existing and existing.sent.get("sent"):
        return json_error("Cannot re-ingest a week that has already been sent", status=409)

    try:
        games = generate_games.scrape_athletics_schedule(week_id, end_date_str)
        arts_events = generate_games.fetch_arts_events(week_id, end_date_str)
    except Exception as exc:  # noqa: BLE001
        return json_error(f"Scraping failed: {exc}", status=503)

    all_events = games + arts_events
    source_summary = {
        "sportsGames": len(games),
        "artsEvents": len(arts_events),
        "totalEvents": len(all_events),
    }

    timestamp = utc_now_iso()
    event_payloads = [
        source_event_to_weekly_event_payload(
            event,
            school_bucket="middle_school" if generate_games.is_middle_school_game(getattr(event, "team", "")) else "upper_school",
            is_varsity_game=generate_games.is_varsity_game,
            timestamp=timestamp,
        )
        for event in all_events
    ]

    payload = {
        "start_date": week_id,
        "end_date": end_date_str,
        "heading": existing.heading if existing else DEFAULT_HEADING,
        "notes": existing.notes if existing else "",
        "events": event_payloads,
        "source_summary": source_summary,
        "ingest_context": {
            "runner": "web-ui",
            "last_ingested_at": timestamp,
        },
    }

    try:
        week = get_emails_store().save_week(week_id, payload)
    except (ValueError, RuntimeError) as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "source_summary": source_summary})


@blueprint.get("/weeks/<week_id>/sender-output")
@open_emails_access
def sender_output(week_id: str) -> Any:
    week = get_emails_store().get_week(week_id)
    if week is None:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    if not week.approval.get("approved"):
        return json_error("Week must be approved before sender output can be fetched", status=409)

    audience = str(request.args.get("audience", "")).strip().lower()
    try:
        outputs = build_weekly_email_outputs(week)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    if audience:
        selected = outputs.get(audience)
        if selected is None:
            return json_error("Audience must be one of: middle-school, upper-school", status=400)
        return jsonify({"ok": True, "week_id": week_id, "approved": True, "output": selected, "sent": week.sent})

    return jsonify({"ok": True, "week_id": week_id, "approved": True, "outputs": outputs, "sent": week.sent})