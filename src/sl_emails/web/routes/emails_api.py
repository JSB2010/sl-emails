"""Weekly email API routes preserved under the dedicated web package."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from sl_emails.domain.dates import format_email_date_range, week_end_for, week_start_for
from sl_emails.ingest import generate_games
from sl_emails.services.gemini_copy import GeminiCopyError, generate_week_copy
from sl_emails.services.request_store import event_payload_for_request
from sl_emails.services.weekly_ingest import WeeklyIngestResult, WeeklySourceFetchError, scheduled_ingest_week, source_refresh_week
from sl_emails.services.weekly_outputs import build_weekly_email_outputs as render_weekly_email_outputs
from sl_emails.services.weekly_store import build_blank_week_payload
from sl_emails.web.request_protection import HONEYPOT_FIELD, RequestProtectionError, first_forwarded_ip

from ..support import current_public_base_url, current_user_email, get_activity_store, get_emails_store, get_request_protector, get_request_store, json_error, require_automation_key, require_emails_admin, require_emails_operator, update_week_metadata_safely, write_activity


blueprint = Blueprint("emails_api", __name__, url_prefix="/api/emails")


def build_weekly_email_outputs(week: Any) -> dict[str, dict[str, Any]]:
    return render_weekly_email_outputs(
        week,
        generate_games_module=generate_games,
        icon_base_url=current_public_base_url(),
    )


def canonical_week_id(week_id: str) -> str:
    return week_start_for(week_id)


def serialize_ingest_result(result: WeeklyIngestResult) -> Any:
    return jsonify(
        {
            "ok": True,
            "week_id": result.week_id,
            "action": result.action,
            "reason": result.reason,
            "source_summary": result.source_summary,
            "source_health": result.source_health,
            "week": result.week.to_dict(),
        }
    )


def actor_for_request(default: str = "admin-ui") -> str:
    actor = str(request.headers.get("X-Email-Actor") or current_user_email() or default).strip()
    return actor or default


def update_week_status(week_id: str, patch: dict[str, Any]) -> Any:
    return update_week_metadata_safely(week_id, patch)


def value_error_status(exc: ValueError) -> int:
    message = str(exc).lower()
    if any(
        token in message
        for token in (
            "locked for sending",
            "already claimed for sending",
            "must be approved before",
            "claimed for sending before it can be marked sent",
            "only pending requests can be reviewed",
            "no email this week",
        )
    ):
        return 409
    return 400


@blueprint.post("/requests")
def submit_event_request() -> Any:
    payload = request.get_json(silent=True) or {}
    protector = get_request_protector()
    remote_addr = first_forwarded_ip(request.headers.get("X-Forwarded-For", ""), request.remote_addr or "")
    user_agent = str(request.headers.get("User-Agent") or "").strip()
    try:
        protector.validate_honeypot(payload)
        protector.check_rate_limit(f"{remote_addr}|{user_agent[:128]}")
    except RequestProtectionError as exc:
        return json_error(str(exc), status=getattr(exc, "status_code", 400))

    payload.pop(HONEYPOT_FIELD, None)
    payload["metadata"] = {
        **(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
        "submission": protector.submission_metadata(
            remote_addr=remote_addr,
            user_agent=user_agent,
            referrer=str(request.headers.get("Referer") or "").strip(),
        ),
    }
    try:
        record = get_request_store().submit_request(payload)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(
        event_type="request.submitted",
        status="success",
        actor=record.requester_email or record.requester_name or "public-request",
        week_id=record.week_id,
        message="Submitted public event request",
        details={"request_id": record.request_id, "requester_name": record.requester_name},
    )
    return jsonify(
        {
            "ok": True,
            "request": record.to_dict(),
            "week_label": format_email_date_range(record.week_id, week_end_for(record.week_id)),
        }
    ), 201


@blueprint.get("/weeks/<week_id>")
@require_emails_admin
def get_week(week_id: str) -> Any:
    normalized_week_id = canonical_week_id(week_id)
    week = get_emails_store().get_week(normalized_week_id)
    if week is None:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.put("/weeks/<week_id>")
@require_emails_admin
def save_week(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    if isinstance(payload.get("delivery"), dict):
        payload["delivery"] = {**payload["delivery"], "updated_by": actor}
    try:
        week = get_emails_store().save_week(normalized_week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="draft.saved", status="success", actor=actor, week_id=normalized_week_id, message="Saved weekly draft")
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.post("/weeks/<week_id>/source-refresh")
@require_emails_admin
def source_refresh(week_id: str) -> Any:
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    try:
        result = source_refresh_week(get_emails_store(), normalized_week_id)
        updated_week = update_week_status(
            normalized_week_id,
            {
                "manual_refresh": {
                    "status": "success",
                    "action": result.action,
                    "reason": result.reason,
                    "actor": actor,
                    "occurred_at": result.week.updated_at,
                    "source_summary": result.source_summary,
                    "source_health": result.source_health,
                }
            },
        )
        if updated_week is not None:
            result.week = updated_week
    except WeeklySourceFetchError as exc:
        update_week_status(
            normalized_week_id,
            {
                "manual_refresh": {
                    "status": "failed",
                    "actor": actor,
                    "occurred_at": "",
                    "message": str(exc),
                    "source_health": exc.source_health,
                }
            },
        )
        write_activity(
            event_type="source_refresh",
            status="failed",
            actor=actor,
            week_id=normalized_week_id,
            message=str(exc),
            details={"source_health": exc.source_health},
        )
        return json_error(str(exc), status=503, extra={"source_health": exc.source_health})
    except ValueError as exc:
        write_activity(event_type="source_refresh", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc))
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        write_activity(event_type="source_refresh", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc))
        return json_error(str(exc), status=503)

    write_activity(
        event_type="source_refresh",
        status="success",
        actor=actor,
        week_id=normalized_week_id,
        message="Refreshed source events for weekly draft",
        details={"action": result.action, "reason": result.reason, "source_summary": result.source_summary, "source_health": result.source_health},
    )
    return serialize_ingest_result(result)


@blueprint.post("/weeks/<week_id>/events")
@require_emails_admin
def create_custom_event(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    try:
        week = get_emails_store().add_event(normalized_week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="custom_event.created", status="success", actor=actor, week_id=normalized_week_id, message="Added custom event")
    return jsonify({"ok": True, "week": week.to_dict(), "event": week.events[-1].to_dict() if week.events else None}), 201


@blueprint.post("/weeks/<week_id>/clear")
@require_emails_admin
def clear_week(week_id: str) -> Any:
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    existing = get_emails_store().get_week(normalized_week_id)
    if existing is None:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)

    payload = build_blank_week_payload(normalized_week_id)
    payload["metadata"] = existing.metadata
    payload["delivery"] = {**payload["delivery"], "updated_by": actor}
    try:
        week = get_emails_store().save_week(normalized_week_id, payload)
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="draft.cleared", status="success", actor=actor, week_id=normalized_week_id, message="Cleared weekly draft")
    return jsonify({"ok": True, "week": week.to_dict()})


@blueprint.get("/weeks/<week_id>/requests")
@require_emails_admin
def list_week_requests(week_id: str) -> Any:
    normalized_week_id = canonical_week_id(week_id)
    try:
        records = get_request_store().list_requests(normalized_week_id)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)
    return jsonify({"ok": True, "requests": [record.to_dict() for record in records]})


@blueprint.post("/weeks/<week_id>/requests/<request_id>/approve")
@require_emails_admin
def approve_event_request(week_id: str, request_id: str) -> Any:
    actor = actor_for_request()
    payload = request.get_json(silent=True) or {}
    normalized_week_id = canonical_week_id(week_id)
    request_store = get_request_store()
    emails_store = get_emails_store()
    request_record = request_store.get_request(normalized_week_id, request_id)
    if request_record is None:
        return json_error("No event request found for that week", status=404)
    if request_record.status != "pending":
        return json_error("Only pending requests can be reviewed", status=409)

    try:
        approve_into_week = getattr(request_store, "approve_request_into_week", None)
        if callable(approve_into_week):
            try:
                    updated_request, week = approve_into_week(
                    normalized_week_id,
                    request_id,
                    reviewed_by=actor,
                    reviewer_notes=str(payload.get("reviewer_notes") or "").strip(),
                )
            except NotImplementedError:
                existing_week = emails_store.get_week(normalized_week_id)
                event_payload = event_payload_for_request(request_record)
                week = emails_store.add_event(normalized_week_id, event_payload)
                try:
                    updated_request = request_store.review_request(
                        normalized_week_id,
                        request_id,
                        decision="approved",
                        reviewed_by=actor,
                        reviewer_notes=str(payload.get("reviewer_notes") or "").strip(),
                        resolved_event_id=str(event_payload["id"]),
                    )
                except Exception:
                    if existing_week is not None:
                        emails_store.save_week(normalized_week_id, existing_week.to_dict())
                    raise
        else:
            event_payload = event_payload_for_request(request_record)
            week = emails_store.add_event(normalized_week_id, event_payload)
            updated_request = request_store.review_request(
                normalized_week_id,
                request_id,
                decision="approved",
                reviewed_by=actor,
                reviewer_notes=str(payload.get("reviewer_notes") or "").strip(),
                resolved_event_id=str(event_payload["id"]),
            )
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except KeyError:
        return json_error("No event request found for that week", status=404)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(
        event_type="request.reviewed",
        status="success",
        actor=actor,
        week_id=normalized_week_id,
        message="Approved event request",
        details={"request_id": request_id, "decision": "approved", "requester_email": request_record.requester_email},
    )
    return jsonify({"ok": True, "request": updated_request.to_dict(), "week": week.to_dict()})


@blueprint.post("/weeks/<week_id>/requests/<request_id>/deny")
@require_emails_admin
def deny_event_request(week_id: str, request_id: str) -> Any:
    actor = actor_for_request()
    payload = request.get_json(silent=True) or {}
    normalized_week_id = canonical_week_id(week_id)
    request_record = get_request_store().get_request(normalized_week_id, request_id)
    if request_record is None:
        return json_error("No event request found for that week", status=404)
    if request_record.status != "pending":
        return json_error("Only pending requests can be reviewed", status=409)

    try:
        updated_request = get_request_store().review_request(
            normalized_week_id,
            request_id,
            decision="denied",
            reviewed_by=actor,
            reviewer_notes=str(payload.get("reviewer_notes") or "").strip(),
        )
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(
        event_type="request.reviewed",
        status="success",
        actor=actor,
        week_id=normalized_week_id,
        message="Denied event request",
        details={"request_id": request_id, "decision": "denied", "requester_email": request_record.requester_email},
    )
    return jsonify({"ok": True, "request": updated_request.to_dict()})


@blueprint.post("/weeks/<week_id>/preview")
@require_emails_admin
def preview_week(week_id: str) -> Any:
    normalized_week_id = canonical_week_id(week_id)
    week = get_emails_store().get_week(normalized_week_id)
    if week is None:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)

    try:
        outputs = build_weekly_email_outputs(week)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.post("/weeks/<week_id>/ai-copy")
@require_emails_admin
def generate_ai_copy(week_id: str) -> Any:
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    store = get_emails_store()
    existing = store.get_week(normalized_week_id)
    if existing is None:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)

    try:
        generated = generate_week_copy(
            existing,
            api_key=str(current_app.config.get("GEMINI_API_KEY") or ""),
            model=str(current_app.config.get("GEMINI_MODEL") or "gemini-3-flash-preview"),
        )
    except GeminiCopyError as exc:
        return json_error(str(exc), status=503)

    payload = existing.to_dict()
    if generated.get("heading"):
        payload["heading"] = generated["heading"]
    payload["notes"] = generated.get("notes") if generated.get("notes") is not None else payload.get("notes")
    payload["subject_overrides"] = generated.get("subject_overrides") or {}
    payload["copy_overrides"] = generated.get("copy_overrides") or {}
    payload["copy_overrides_by_audience"] = generated.get("copy_overrides_by_audience") or {}
    payload["delivery"] = {**(payload.get("delivery") or {}), "updated_by": actor}
    try:
        week = store.save_week(normalized_week_id, payload)
        outputs = build_weekly_email_outputs(week)
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="ai_copy.generated", status="success", actor=actor, week_id=normalized_week_id, message="Generated weekly copy with Gemini")
    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.get("/weeks/<week_id>/activity")
@require_emails_admin
def list_week_activity(week_id: str) -> Any:
    normalized_week_id = canonical_week_id(week_id)
    limit_raw = str(request.args.get("limit") or "").strip()
    try:
        limit = max(1, min(int(limit_raw or "20"), 100))
    except ValueError:
        return json_error("limit must be an integer between 1 and 100", status=400)
    try:
        records = get_activity_store().list_recent(week_id=normalized_week_id, limit=limit)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)
    return jsonify({"ok": True, "activity": [record.to_dict() for record in records]})


@blueprint.post("/weeks/<week_id>/approve")
@require_emails_admin
def approve_week(week_id: str) -> Any:
    actor = actor_for_request()
    normalized_week_id = canonical_week_id(week_id)
    try:
        week = get_emails_store().approve_week(normalized_week_id, approved_by=actor)
        outputs = build_weekly_email_outputs(week)
        updated_week = update_week_status(
            normalized_week_id,
            {
                "approval": {
                    "status": "approved",
                    "actor": actor,
                    "occurred_at": week.approval.get("approved_at") or week.updated_at,
                }
            },
        )
        if updated_week is not None:
            week = updated_week
    except KeyError:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)
    except ValueError as exc:
        return json_error(str(exc), status=value_error_status(exc))
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(event_type="approval", status="success", actor=actor, week_id=normalized_week_id, message="Approved weekly draft")
    return jsonify({"ok": True, "week": week.to_dict(), "outputs": outputs})


@blueprint.post("/weeks/<week_id>/sent")
@require_emails_operator
def mark_week_sent(week_id: str) -> Any:
    actor = actor_for_request("automation")
    payload = request.get_json(silent=True) or {}
    normalized_week_id = canonical_week_id(week_id)
    requested_state = str(payload.get("state") or "sent").strip().lower() or "sent"
    if requested_state not in {"sending", "sent", "unsent"}:
        return json_error("state must be one of: sending, sent, unsent", status=400)

    try:
        if requested_state == "sending":
            week = get_emails_store().claim_week_send(normalized_week_id, sending_by=actor)
            updated_week = update_week_status(
                normalized_week_id,
                {
                    "send": {
                        "status": "sending",
                        "actor": actor,
                        "occurred_at": week.sent.get("sending_at") or week.updated_at,
                    }
                },
            )
            if updated_week is not None:
                week = updated_week
        elif requested_state == "unsent":
            week = get_emails_store().reset_week_send(normalized_week_id)
            updated_week = update_week_status(
                normalized_week_id,
                {
                    "send": {
                        "status": "reset",
                        "actor": actor,
                        "occurred_at": week.updated_at,
                    }
                },
            )
            if updated_week is not None:
                week = updated_week
        else:
            week = get_emails_store().mark_week_sent(normalized_week_id, sent_by=actor)
            updated_week = update_week_status(
                normalized_week_id,
                {
                    "send": {
                        "status": "sent",
                        "actor": actor,
                        "occurred_at": week.sent.get("sent_at") or week.updated_at,
                    }
                },
            )
            if updated_week is not None:
                week = updated_week
    except KeyError:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)
    except ValueError as exc:
        write_activity(event_type="send", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc), details={"state": requested_state})
        return json_error(str(exc), status=409)
    except RuntimeError as exc:
        write_activity(event_type="send", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc), details={"state": requested_state})
        return json_error(str(exc), status=503)

    write_activity(event_type="send", status="success", actor=actor, week_id=normalized_week_id, message=f"Updated send state to {requested_state}")
    return jsonify({"ok": True, "week": week.to_dict(), "sent": week.sent})


@blueprint.get("/weeks/<week_id>/sender-output")
@require_emails_operator
def sender_output(week_id: str) -> Any:
    normalized_week_id = canonical_week_id(week_id)
    week = get_emails_store().get_week(normalized_week_id)
    if week is None:
        return json_error(f"No weekly draft found for {normalized_week_id}", status=404)

    audience = str(request.args.get("audience", "")).strip().lower()
    if not week.approval.get("approved"):
        if audience and audience not in {"middle-school", "upper-school"}:
            return json_error("Audience must be one of: middle-school, upper-school", status=400)
        payload: dict[str, Any] = {
            "ok": True,
            "week_id": normalized_week_id,
            "approved": False,
            "sent": week.sent,
            "delivery": week.delivery,
        }
        if audience:
            payload["output"] = None
        else:
            payload["outputs"] = {}
        return jsonify(payload)

    try:
        outputs = build_weekly_email_outputs(week)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    if audience:
        selected = outputs.get(audience)
        if selected is None:
            return json_error("Audience must be one of: middle-school, upper-school", status=400)
        return jsonify({"ok": True, "week_id": normalized_week_id, "approved": True, "output": selected, "sent": week.sent, "delivery": week.delivery})

    return jsonify({"ok": True, "week_id": normalized_week_id, "approved": True, "outputs": outputs, "sent": week.sent, "delivery": week.delivery})


@blueprint.post("/automation/weeks/<week_id>/scheduled-ingest")
@require_automation_key
def scheduled_ingest(week_id: str) -> Any:
    actor = actor_for_request("google-apps-script")
    normalized_week_id = canonical_week_id(week_id)
    try:
        result = scheduled_ingest_week(get_emails_store(), normalized_week_id)
        updated_week = update_week_status(
            normalized_week_id,
            {
                "scheduled_ingest": {
                    "status": "success",
                    "action": result.action,
                    "reason": result.reason,
                    "actor": actor,
                    "occurred_at": result.week.updated_at,
                    "source_summary": result.source_summary,
                    "source_health": result.source_health,
                }
            },
        )
        if updated_week is not None:
            result.week = updated_week
    except WeeklySourceFetchError as exc:
        update_week_status(
            normalized_week_id,
            {
                "scheduled_ingest": {
                    "status": "failed",
                    "actor": actor,
                    "occurred_at": "",
                    "message": str(exc),
                    "source_health": exc.source_health,
                }
            },
        )
        write_activity(
            event_type="scheduled_ingest",
            status="failed",
            actor=actor,
            week_id=normalized_week_id,
            message=str(exc),
            details={"source_health": exc.source_health},
        )
        return json_error(str(exc), status=503, extra={"source_health": exc.source_health})
    except ValueError as exc:
        write_activity(event_type="scheduled_ingest", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc))
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        write_activity(event_type="scheduled_ingest", status="failed", actor=actor, week_id=normalized_week_id, message=str(exc))
        return json_error(str(exc), status=503)

    write_activity(
        event_type="scheduled_ingest",
        status="success",
        actor=actor,
        week_id=normalized_week_id,
        message=f"Scheduled ingest {result.action}",
        details={"reason": result.reason, "source_summary": result.source_summary, "source_health": result.source_health},
    )
    return serialize_ingest_result(result)


@blueprint.post("/automation/weeks/<week_id>/activity")
@require_automation_key
def log_automation_activity(week_id: str) -> Any:
    payload = request.get_json(silent=True) or {}
    normalized_week_id = canonical_week_id(week_id)
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
        week_id=normalized_week_id,
        message=message,
        details=details,
    )
    try:
        update_week_status(normalized_week_id, {event_type: {"status": status, "actor": actor, "message": message, "occurred_at": details.get("occurred_at") or "", **details}})
    except KeyError:
        pass

    return jsonify({"ok": True})
