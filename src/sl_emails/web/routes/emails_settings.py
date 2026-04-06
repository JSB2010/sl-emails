from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, render_template, request

from sl_emails.services.admin_settings import build_automation_settings_payload, normalize_email, normalize_email_list, normalize_sender_metadata, validate_sender_metadata

from ..support import auth_urls, current_user, ensure_admin_settings, get_settings_store, json_error, require_automation_key, require_emails_admin, write_activity


blueprint = Blueprint("emails_settings", __name__)


def _serialize_settings() -> dict[str, Any]:
    settings = ensure_admin_settings()
    return {
        "allowed_admin_emails": settings.allowed_admin_emails,
        "ops_notification_emails": settings.ops_notification_emails,
        "sender_metadata": normalize_sender_metadata(settings.sender_metadata),
        "created_at": settings.created_at,
        "created_by": settings.created_by,
        "updated_at": settings.updated_at,
        "updated_by": settings.updated_by,
    }


@blueprint.get("/emails/settings")
@require_emails_admin
def settings_page() -> Any:
    user = current_user() or {}
    return render_template(
        "emails_settings.html",
        current_user_email=str(user.get("email") or ""),
        current_user_name=str(user.get("name") or ""),
        auth=auth_urls(),
        review_url="/emails",
        settings_payload=_serialize_settings(),
    )


@blueprint.get("/api/emails/settings")
@require_emails_admin
def get_settings() -> Any:
    return jsonify({"ok": True, "settings": _serialize_settings()})


@blueprint.get("/api/emails/automation/settings")
@require_automation_key
def get_automation_settings() -> Any:
    settings = ensure_admin_settings()
    return jsonify({"ok": True, "config": build_automation_settings_payload(settings)})


@blueprint.put("/api/emails/settings")
@require_emails_admin
def update_settings() -> Any:
    payload = request.get_json(silent=True) or {}
    actor = normalize_email(str((current_user() or {}).get("email") or "admin"))

    try:
        allowed_admin_emails = normalize_email_list(payload.get("allowed_admin_emails"))
        ops_notification_emails = normalize_email_list(payload.get("ops_notification_emails"))
    except ValueError as exc:
        return json_error(str(exc), status=400)

    if not allowed_admin_emails:
        return json_error("At least one allowed admin email is required", status=400)
    if actor and actor not in allowed_admin_emails:
        return json_error("You cannot remove your own email from the allowlist while signed in", status=400)

    existing = ensure_admin_settings()
    if len(existing.allowed_admin_emails) == 1 and set(allowed_admin_emails) != set(existing.allowed_admin_emails):
        return json_error("You cannot remove the last allowed admin", status=400)
    try:
        sender_metadata_source = payload.get("sender_metadata") if payload.get("sender_metadata") is not None else existing.sender_metadata
        sender_metadata = validate_sender_metadata(sender_metadata_source)
    except ValueError as exc:
        return json_error(str(exc), status=400)

    settings = get_settings_store().update_settings(
        allowed_admin_emails=allowed_admin_emails,
        ops_notification_emails=ops_notification_emails,
        sender_metadata=sender_metadata,
        actor=actor or "admin",
    )
    write_activity(
        event_type="settings.updated",
        status="success",
        actor=actor or "admin",
        message="Updated sports email admin settings",
        details={
            "allowed_admin_emails": settings.allowed_admin_emails,
            "ops_notification_emails": settings.ops_notification_emails,
            "sender_metadata": normalize_sender_metadata(settings.sender_metadata),
        },
    )
    return jsonify({"ok": True, "settings": _serialize_settings()})
