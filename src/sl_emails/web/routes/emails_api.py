"""Weekly email API routes preserved under the dedicated web package."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from sl_emails.ingest import generate_games
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