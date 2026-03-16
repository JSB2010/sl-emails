"""Weekly email API routes preserved under the dedicated web package."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from sl_emails.ingest import generate_games
from sl_emails.services.weekly_ingest import WeeklyIngestResult, scheduled_ingest_week, source_refresh_week
from sl_emails.services.weekly_outputs import build_weekly_email_outputs as render_weekly_email_outputs

from ..support import current_user_email, get_emails_store, json_error, require_automation_key, require_emails_admin, require_emails_operator, write_activity


blueprint = Blueprint("emails_api", __name__, url_prefix="/api/emails")


def build_weekly_email_outputs(week: Any) -> dict[str, dict[str, Any]]:
    return render_weekly_email_outputs(week, generate_games_module=generate_games)


def serialize_ingest_result(result: WeeklyIngestResult) -> Any:
    return jsonify(
        {
            "ok": True,
            "week_id": result.week_id,
            "action": result.action,
            "reason": result.reason,
            "source_summary": result.source_summary,
            "week": result.week.to_dict(),
        }
    )


def actor_for_request(default: str = "admin-ui") -> str:
    actor = str(request.headers.get("X-Email-Actor") or current_user_email() or default).strip()
    return actor or default


def update_week_status(week_id: str, patch: dict[str, Any]) -> Any:
    return get_emails_store().update_week_metadata(week_id, patch)


@blueprint.get("/weeks/<week_id>")
@require_emails_admin
def get_week(week_id: str) -> Any:
    week = get_emails_store().get_week(week_id)
    if week is None:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.put("/weeks/<week_id>")
@require_emails_admin
def save_week(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    actor = actor_for_request()
    try:
        week = get_emails_store().save_week(week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="draft.saved", status="success", actor=actor, week_id=week_id, message="Saved weekly draft")
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.post("/weeks/<week_id>/source-refresh")
@require_emails_admin
def source_refresh(week_id: str) -> Any:
    actor = actor_for_request()
    try:
        result = source_refresh_week(get_emails_store(), week_id)
        result.week = update_week_status(
            week_id,
            {
                "manual_refresh": {
                    "status": "success",
                    "action": result.action,
                    "reason": result.reason,
                    "actor": actor,
                    "occurred_at": result.week.updated_at,
                    "source_summary": result.source_summary,
                }
            },
        )
    except ValueError as exc:
        write_activity(event_type="source_refresh", status="failed", actor=actor, week_id=week_id, message=str(exc))
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        write_activity(event_type="source_refresh", status="failed", actor=actor, week_id=week_id, message=str(exc))
        return json_error(str(exc), status=503)

    write_activity(
        event_type="source_refresh",
        status="success",
        actor=actor,
        week_id=week_id,
        message="Refreshed source events for weekly draft",
        details={"action": result.action, "reason": result.reason, "source_summary": result.source_summary},
    )
    return serialize_ingest_result(result)


@blueprint.post("/weeks/<week_id>/events")
@require_emails_admin
def create_custom_event(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    actor = actor_for_request()
    try:
        week = get_emails_store().add_event(week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="custom_event.created", status="success", actor=actor, week_id=week_id, message="Added custom event")
    return jsonify({"ok": True, "week": week.to_dict(), "event": week.events[-1].to_dict() if week.events else None}), 201


@blueprint.post("/weeks/<week_id>/preview")
@require_emails_admin
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
@require_emails_admin
def approve_week(week_id: str) -> Any:
    actor = actor_for_request()
    try:
        week = get_emails_store().approve_week(week_id, approved_by=actor)
        outputs = build_weekly_email_outputs(week)
        week = update_week_status(
            week_id,
            {
                "approval": {
                    "status": "approved",
                    "actor": actor,
                    "occurred_at": week.approval.get("approved_at") or week.updated_at,
                }
            },
        )
    except KeyError:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="approval", status="success", actor=actor, week_id=week_id, message="Approved weekly draft")
    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.post("/weeks/<week_id>/sent")
@require_emails_operator
def mark_week_sent(week_id: str) -> Any:
    actor = actor_for_request("automation")
    payload = request.get_json(silent=True) or {}
    requested_state = str(payload.get("state") or "sent").strip().lower() or "sent"
    if requested_state not in {"sending", "sent", "unsent"}:
        return json_error("state must be one of: sending, sent, unsent", status=400)

    try:
        if requested_state == "sending":
            week = get_emails_store().claim_week_send(week_id, sending_by=actor)
            week = update_week_status(
                week_id,
                {
                    "send": {
                        "status": "sending",
                        "actor": actor,
                        "occurred_at": week.sent.get("sending_at") or week.updated_at,
                    }
                },
            )
        elif requested_state == "unsent":
            week = get_emails_store().reset_week_send(week_id)
            week = update_week_status(
                week_id,
                {
                    "send": {
                        "status": "reset",
                        "actor": actor,
                        "occurred_at": week.updated_at,
                    }
                },
            )
        else:
            week = get_emails_store().mark_week_sent(week_id, sent_by=actor)
            week = update_week_status(
                week_id,
                {
                    "send": {
                        "status": "sent",
                        "actor": actor,
                        "occurred_at": week.sent.get("sent_at") or week.updated_at,
                    }
                },
            )
    except KeyError:
        return json_error(f"No weekly draft found for {week_id}", status=404)
    except ValueError as exc:
        write_activity(event_type="send", status="failed", actor=actor, week_id=week_id, message=str(exc), details={"state": requested_state})
        return json_error(str(exc), status=409)
    except RuntimeError as exc:
        write_activity(event_type="send", status="failed", actor=actor, week_id=week_id, message=str(exc), details={"state": requested_state})
        return json_error(str(exc), status=503)

    write_activity(event_type="send", status="success", actor=actor, week_id=week_id, message=f"Updated send state to {requested_state}")
    return jsonify({"ok": True, "week": week.to_dict(), "sent": week.sent})


@blueprint.get("/weeks/<week_id>/sender-output")
@require_emails_operator
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


@blueprint.post("/automation/weeks/<week_id>/scheduled-ingest")
@require_automation_key
def scheduled_ingest(week_id: str) -> Any:
    actor = actor_for_request("google-apps-script")
    try:
        result = scheduled_ingest_week(get_emails_store(), week_id)
        result.week = update_week_status(
            week_id,
            {
                "scheduled_ingest": {
                    "status": "success",
                    "action": result.action,
                    "reason": result.reason,
                    "actor": actor,
                    "occurred_at": result.week.updated_at,
                    "source_summary": result.source_summary,
                }
            },
        )
    except ValueError as exc:
        write_activity(event_type="scheduled_ingest", status="failed", actor=actor, week_id=week_id, message=str(exc))
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        write_activity(event_type="scheduled_ingest", status="failed", actor=actor, week_id=week_id, message=str(exc))
        return json_error(str(exc), status=503)

    write_activity(
        event_type="scheduled_ingest",
        status="success",
        actor=actor,
        week_id=week_id,
        message=f"Scheduled ingest {result.action}",
        details={"reason": result.reason, "source_summary": result.source_summary},
    )
    return serialize_ingest_result(result)


@blueprint.post("/automation/weeks/<week_id>/activity")
@require_automation_key
def log_automation_activity(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    event_type = str(payload.get("event_type") or "").strip().lower()
    status = str(payload.get("status") or "").strip().lower()
    actor = actor_for_request("google-apps-script")
    message = str(payload.get("message") or "").strip()
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}

    if not event_type or not status:
        return json_error("event_type and status are required", status=400)

    write_activity(
        event_type=event_type,
        status=status,
        actor=actor,
        week_id=week_id,
        message=message,
        details=details,
    )
    try:
        update_week_status(week_id, {event_type: {"status": status, "actor": actor, "message": message, "occurred_at": details.get("occurred_at") or "", **details}})
    except KeyError:
        pass

    return jsonify({"ok": True})
