"""Shared runtime helpers for the dedicated Flask web package."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable
from urllib.parse import quote

from flask import Response, current_app, jsonify, redirect, request, session, url_for

from sl_emails.config import EMAILS_AUTOMATION_KEY_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV
from sl_emails.config import SIGNAGE_TIMEZONE
from sl_emails.config import WEB_STATIC_DIR as STATIC_DIR
from sl_emails.config import WEB_TEMPLATES_DIR as TEMPLATE_DIR
from sl_emails.domain.dates import today_in_timezone
from sl_emails.services.activity_log import FirestoreActivityLogStore
from sl_emails.services.admin_settings import DEFAULT_ALLOWED_ADMIN_EMAILS, FirestoreAdminSettingsStore, normalize_email_list
from sl_emails.services.request_store import FirestoreEventRequestStore
from sl_emails.services.signage_store import FirestoreSignageStore
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore
from sl_emails.signage.generate_signage import generate_signage_html
from sl_emails.web.request_protection import PublicRequestProtector


def get_emails_store() -> FirestoreWeeklyEmailStore:
    store = current_app.config.get("EMAILS_STORE")
    if store is None:
        store = FirestoreWeeklyEmailStore()
        current_app.config["EMAILS_STORE"] = store
    return store


def get_signage_store() -> FirestoreSignageStore:
    store = current_app.config.get("SIGNAGE_STORE")
    if store is None:
        store = FirestoreSignageStore()
        current_app.config["SIGNAGE_STORE"] = store
    return store


def get_settings_store() -> FirestoreAdminSettingsStore:
    store = current_app.config.get("EMAILS_SETTINGS_STORE")
    if store is None:
        store = FirestoreAdminSettingsStore()
        current_app.config["EMAILS_SETTINGS_STORE"] = store
    return store


def get_request_store() -> FirestoreEventRequestStore:
    store = current_app.config.get("EMAILS_REQUEST_STORE")
    if store is None:
        store = FirestoreEventRequestStore()
        current_app.config["EMAILS_REQUEST_STORE"] = store
    return store


def get_activity_store() -> FirestoreActivityLogStore:
    store = current_app.config.get("EMAILS_ACTIVITY_STORE")
    if store is None:
        store = FirestoreActivityLogStore()
        current_app.config["EMAILS_ACTIVITY_STORE"] = store
    return store


def get_request_protector() -> PublicRequestProtector:
    protector = current_app.config.get("EMAILS_REQUEST_PROTECTOR")
    if protector is None:
        protector = PublicRequestProtector()
        current_app.config["EMAILS_REQUEST_PROTECTOR"] = protector
    return protector


def bootstrap_admin_emails() -> list[str]:
    raw = current_app.config.get("EMAILS_BOOTSTRAP_ALLOWED_EMAILS") or current_app.config.get(EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV) or DEFAULT_ALLOWED_ADMIN_EMAILS
    return normalize_email_list(raw)


def bootstrap_notification_emails() -> list[str]:
    raw = current_app.config.get("EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS") or current_app.config.get(EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV) or bootstrap_admin_emails()
    return normalize_email_list(raw)


def ensure_admin_settings():
    return get_settings_store().ensure_settings(
        allowed_admin_emails=bootstrap_admin_emails(),
        ops_notification_emails=bootstrap_notification_emails(),
        actor="bootstrap",
    )


def serve_signage() -> Response:
    day_id = today_in_timezone(SIGNAGE_TIMEZONE).isoformat()
    try:
        day = get_signage_store().get_day(day_id)
    except RuntimeError as exc:
        return Response(str(exc), status=503, mimetype="text/plain")
    if day is None:
        return Response("Signage snapshot not found.", status=404, mimetype="text/plain")
    return Response(generate_signage_html(day.poster_events(), day_id), mimetype="text/html")


def json_error(message: str, status: int = 400, *, extra: dict[str, Any] | None = None) -> tuple[Response, int]:
    payload = {"ok": False, "error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), status


def _request_next_url() -> str:
    full_path = request.full_path if request.query_string else request.path
    return str(full_path or "/emails").rstrip("?")


def current_user() -> dict[str, Any] | None:
    user = session.get("auth_user")
    return dict(user) if isinstance(user, dict) else None


def current_user_email() -> str:
    user = current_user() or {}
    return str(user.get("email") or "").strip().lower()


def is_authenticated_admin() -> bool:
    email = current_user_email()
    if not email:
        return False
    settings = ensure_admin_settings()
    return email in settings.allowed_admin_emails


def auth_urls() -> dict[str, str]:
    next_url = _request_next_url()
    return {
        "login": f"{url_for('auth.login')}?next={quote(next_url, safe='/?=&-%')}",
        "logout": url_for("auth.logout"),
        "settings": url_for("emails_settings.settings_page"),
    }


def _unauthorized_response() -> Any:
    login_url = auth_urls()["login"]
    if request.path.startswith("/api/"):
        return json_error("Authentication required", status=401, extra={"login_url": login_url})
    return redirect(login_url)


def _forbidden_response() -> Any:
    denied_url = url_for("auth.access_denied")
    if request.path.startswith("/api/"):
        return json_error("Access denied", status=403, extra={"access_denied_url": denied_url})
    return redirect(denied_url)


def require_emails_admin(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any):
        if not current_user_email():
            return _unauthorized_response()
        if not is_authenticated_admin():
            return _forbidden_response()
        return view_func(*args, **kwargs)

    return wrapped


def has_valid_automation_key() -> bool:
    configured_key = str(
        current_app.config.get("EMAILS_AUTOMATION_KEY")
        or current_app.config.get(EMAILS_AUTOMATION_KEY_ENV)
        or ""
    ).strip()
    supplied_key = str(request.headers.get("X-Automation-Key", "")).strip()
    return bool(configured_key and supplied_key == configured_key)


def require_emails_operator(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any):
        if has_valid_automation_key():
            return view_func(*args, **kwargs)
        return require_emails_admin(view_func)(*args, **kwargs)

    return wrapped


def require_automation_key(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any):
        configured_key = str(current_app.config.get("EMAILS_AUTOMATION_KEY") or current_app.config.get(EMAILS_AUTOMATION_KEY_ENV) or "").strip()
        if not configured_key:
            return json_error("Automation key is not configured", status=503)

        if not has_valid_automation_key():
            return json_error("Invalid automation key", status=403)

        return view_func(*args, **kwargs)

    return wrapped


def write_activity(
    *,
    event_type: str,
    status: str,
    actor: str,
    week_id: str = "",
    message: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    get_activity_store().log(
        event_type=event_type,
        status=status,
        actor=actor,
        week_id=week_id,
        message=message,
        details=details or {},
    )


__all__ = [
    "TEMPLATE_DIR",
    "STATIC_DIR",
    "auth_urls",
    "bootstrap_admin_emails",
    "bootstrap_notification_emails",
    "current_user",
    "current_user_email",
    "ensure_admin_settings",
    "get_activity_store",
    "get_emails_store",
    "get_request_store",
    "get_request_protector",
    "get_signage_store",
    "get_settings_store",
    "is_authenticated_admin",
    "json_error",
    "has_valid_automation_key",
    "require_automation_key",
    "require_emails_admin",
    "require_emails_operator",
    "serve_signage",
    "write_activity",
]
