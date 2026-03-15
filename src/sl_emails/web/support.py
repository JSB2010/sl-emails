"""Shared runtime helpers for the dedicated Flask web package."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Response, current_app, jsonify, request

from sl_emails.config import EMAILS_AUTOMATION_KEY_ENV
from sl_emails.config import SIGNAGE_OUTPUT_HTML as SIGNAGE_INDEX
from sl_emails.config import WEB_STATIC_DIR as STATIC_DIR
from sl_emails.config import WEB_TEMPLATES_DIR as TEMPLATE_DIR
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore


def get_emails_store() -> FirestoreWeeklyEmailStore:
    store = current_app.config.get("EMAILS_STORE")
    if store is None:
        store = FirestoreWeeklyEmailStore()
        current_app.config["EMAILS_STORE"] = store
    return store


def serve_signage() -> Response:
    if not SIGNAGE_INDEX.exists():
        return Response("Signage HTML not found.", status=404, mimetype="text/plain")
    return Response(SIGNAGE_INDEX.read_text(encoding="utf-8"), mimetype="text/html")


def json_error(message: str, status: int = 400) -> tuple[Response, int]:
    return jsonify({"ok": False, "error": message}), status


def open_emails_access(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any):
        access_handler = current_app.config.get("EMAILS_ACCESS_HANDLER")
        if callable(access_handler):
            result = access_handler(request)
            if result is not None:
                return result
        return view_func(*args, **kwargs)

    return wrapped


def require_automation_key(view_func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any):
        configured_key = str(
            current_app.config.get("EMAILS_AUTOMATION_KEY")
            or current_app.config.get(EMAILS_AUTOMATION_KEY_ENV)
            or ""
        ).strip()
        if not configured_key:
            return json_error("Automation key is not configured", status=503)

        supplied_key = str(request.headers.get("X-Automation-Key", "")).strip()
        if supplied_key != configured_key:
            return json_error("Invalid automation key", status=403)

        return view_func(*args, **kwargs)

    return wrapped


__all__ = [
    "SIGNAGE_INDEX",
    "TEMPLATE_DIR",
    "STATIC_DIR",
    "get_emails_store",
    "serve_signage",
    "json_error",
    "open_emails_access",
    "require_automation_key",
]
