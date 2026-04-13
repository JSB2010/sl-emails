"""Application factory for the dedicated Flask web runtime package."""

from __future__ import annotations

from typing import Any
import os

from flask import Flask

from sl_emails.config import EMAILS_AUTOMATION_KEY_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV
from sl_emails.config import EMAILS_LOCAL_DEV_ENV
from sl_emails.config import EMAILS_SESSION_SECRET_ENV
from sl_emails.config import GEMINI_API_KEY_ENV
from sl_emails.config import GEMINI_MODEL_ENV
from sl_emails.config import GOOGLE_OAUTH_CALLBACK_URL_ENV
from sl_emails.config import GOOGLE_OAUTH_CLIENT_ID_ENV
from sl_emails.config import GOOGLE_OAUTH_CLIENT_SECRET_ENV
from sl_emails.config import PUBLIC_BASE_URL_ENV

from .google_oauth import init_google_oauth
from .routes import register_routes
from .support import STATIC_DIR, TEMPLATE_DIR


def _flag_enabled(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_local_dev(app: Flask) -> bool:
    return _flag_enabled(app.config.get("EMAILS_LOCAL_DEV"))


def _validate_runtime_config(app: Flask) -> None:
    if app.config.get("TESTING"):
        app.config["SECRET_KEY"] = str(app.config.get("SECRET_KEY") or "sl-emails-test-session-secret")
        return

    required = {
        EMAILS_SESSION_SECRET_ENV: str(app.config.get("SECRET_KEY") or "").strip(),
        GOOGLE_OAUTH_CLIENT_ID_ENV: str(app.config.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip(),
        GOOGLE_OAUTH_CLIENT_SECRET_ENV: str(app.config.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip(),
    }
    if not _is_local_dev(app):
        required[GOOGLE_OAUTH_CALLBACK_URL_ENV] = str(app.config.get("GOOGLE_OAUTH_CALLBACK_URL") or "").strip()
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required runtime configuration: " + ", ".join(missing)
        )


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
    app.config["SECRET_KEY"] = os.getenv(EMAILS_SESSION_SECRET_ENV, "").strip()
    app.config["EMAILS_AUTOMATION_KEY"] = os.getenv(EMAILS_AUTOMATION_KEY_ENV, "").strip()
    app.config["EMAILS_LOCAL_DEV"] = os.getenv(EMAILS_LOCAL_DEV_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv(GOOGLE_OAUTH_CLIENT_ID_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv(GOOGLE_OAUTH_CLIENT_SECRET_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CALLBACK_URL"] = os.getenv(GOOGLE_OAUTH_CALLBACK_URL_ENV, "").strip()
    app.config["GEMINI_API_KEY"] = os.getenv(GEMINI_API_KEY_ENV, "").strip()
    app.config["GEMINI_MODEL"] = os.getenv(GEMINI_MODEL_ENV, "").strip() or "gemini-3-flash-preview"
    app.config["PUBLIC_BASE_URL"] = os.getenv(PUBLIC_BASE_URL_ENV, "").strip()
    app.config["EMAILS_BOOTSTRAP_ALLOWED_EMAILS"] = os.getenv(EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV, "").strip()
    app.config["EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS"] = os.getenv(EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV, "").strip()

    config_overrides = dict(config or {})
    if config_overrides:
        app.config.update(config_overrides)

    local_dev = _is_local_dev(app)
    if "SESSION_COOKIE_HTTPONLY" not in config_overrides:
        app.config["SESSION_COOKIE_HTTPONLY"] = True
    if "SESSION_COOKIE_NAME" not in config_overrides:
        app.config["SESSION_COOKIE_NAME"] = "__session"
    if "SESSION_COOKIE_SAMESITE" not in config_overrides:
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if "SESSION_COOKIE_SECURE" not in config_overrides:
        app.config["SESSION_COOKIE_SECURE"] = not local_dev
    if "PREFERRED_URL_SCHEME" not in config_overrides:
        app.config["PREFERRED_URL_SCHEME"] = "http" if local_dev else "https"

    _validate_runtime_config(app)
    init_google_oauth(app)
    register_routes(app)
    return app


__all__ = ["create_app"]
