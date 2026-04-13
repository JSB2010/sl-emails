from __future__ import annotations

from typing import Any

import requests
from flask import Blueprint, jsonify, render_template, request

from sl_emails.domain.dates import utc_now_iso
from sl_emails.services.admin_settings import (
    build_automation_settings_payload,
    normalize_automation_metadata,
    normalize_email,
    normalize_email_list,
    normalize_sender_metadata,
    validate_automation_metadata,
    validate_sender_metadata,
)

from ..support import auth_urls, current_user, ensure_admin_settings, get_settings_store, is_local_dev_or_testing, json_error, require_automation_key, require_emails_admin, write_activity


blueprint = Blueprint("emails_settings", __name__)


def _serialize_settings() -> dict[str, Any]:
    settings = ensure_admin_settings()
    return {
        "allowed_admin_emails": settings.allowed_admin_emails,
        "ops_notification_emails": settings.ops_notification_emails,
        "sender_metadata": normalize_sender_metadata(settings.sender_metadata),
        "automation_metadata": normalize_automation_metadata(settings.automation_metadata),
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


@blueprint.get("/api/emails/automation/ping")
@require_automation_key
def automation_ping() -> Any:
    return jsonify(
        {
            "ok": True,
            "status": "pong",
            "service": "sl-emails",
            "actor": str(request.headers.get("X-Email-Actor") or "automation"),
            "checked_at": utc_now_iso(),
        }
    )


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
        automation_metadata_source = payload.get("automation_metadata") if payload.get("automation_metadata") is not None else existing.automation_metadata
        automation_metadata = validate_automation_metadata(
            automation_metadata_source,
            require_complete=not is_local_dev_or_testing(),
        )
    except ValueError as exc:
        return json_error(str(exc), status=400)

    settings = get_settings_store().update_settings(
        allowed_admin_emails=allowed_admin_emails,
        ops_notification_emails=ops_notification_emails,
        sender_metadata=sender_metadata,
        automation_metadata=automation_metadata,
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
            "automation_metadata": {
                **normalize_automation_metadata(settings.automation_metadata),
                "automation_key": "[redacted]" if normalize_automation_metadata(settings.automation_metadata)["automation_key"] else "",
            },
        },
    )
    return jsonify({"ok": True, "settings": _serialize_settings()})


@blueprint.post("/api/emails/settings/test-apps-script")
@require_emails_admin
def test_apps_script_connection() -> Any:
    payload = request.get_json(silent=True) or {}
    actor = normalize_email(str((current_user() or {}).get("email") or "admin")) or "admin"
    existing = ensure_admin_settings()
    automation_source = payload.get("automation_metadata") if payload.get("automation_metadata") is not None else existing.automation_metadata

    try:
        automation_metadata = validate_automation_metadata(automation_source, require_complete=True)
    except ValueError as exc:
        return json_error(str(exc), status=400)

    web_app_url = automation_metadata["apps_script_web_app_url"]
    automation_key = automation_metadata["automation_key"]

    try:
        response = requests.post(
            web_app_url,
            json={
                "action": "ping",
                "automation_key": automation_key,
                "actor": actor,
            },
            timeout=20,
            allow_redirects=True,
        )
        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Apps Script returned a non-JSON response ({response.status_code})") from exc
        if response.status_code < 200 or response.status_code >= 300:
            message = (result.get("error") or result.get("message")) if isinstance(result, dict) else ""
            raise RuntimeError(message or f"Apps Script ping failed with status {response.status_code}")
        if not isinstance(result, dict) or result.get("ok") is not True:
            message = (result.get("error") or result.get("message")) if isinstance(result, dict) else ""
            raise RuntimeError(message or "Apps Script ping failed")
    except requests.RequestException as exc:
        message = f"Unable to reach Apps Script web app: {exc}"
        write_activity(event_type="settings.apps_script_test", status="failed", actor=actor, message=message)
        return json_error(message, status=502)
    except RuntimeError as exc:
        message = str(exc)
        write_activity(event_type="settings.apps_script_test", status="failed", actor=actor, message=message)
        return json_error(message, status=502)

    write_activity(
        event_type="settings.apps_script_test",
        status="success",
        actor=actor,
        message="Apps Script web app connection test succeeded",
        details={"apps_script": {key: value for key, value in result.items() if key != "automation_key"}},
    )
    return jsonify({"ok": True, "apps_script": result})
