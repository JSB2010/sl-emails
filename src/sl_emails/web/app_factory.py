"""Application factory for the dedicated Flask web runtime package."""

from __future__ import annotations

from typing import Any
import os

from flask import Flask

from sl_emails.config import EMAILS_AUTOMATION_KEY_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV
from sl_emails.config import EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV
from sl_emails.config import EMAILS_SESSION_SECRET_ENV
from sl_emails.config import GOOGLE_OAUTH_CALLBACK_URL_ENV
from sl_emails.config import GOOGLE_OAUTH_CLIENT_ID_ENV
from sl_emails.config import GOOGLE_OAUTH_CLIENT_SECRET_ENV

from .google_oauth import init_google_oauth
from .routes import register_routes
from .support import STATIC_DIR, TEMPLATE_DIR


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
    app.config["SECRET_KEY"] = os.getenv(EMAILS_SESSION_SECRET_ENV, "").strip() or "sl-emails-dev-session-secret"
    app.config["EMAILS_AUTOMATION_KEY"] = os.getenv(EMAILS_AUTOMATION_KEY_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv(GOOGLE_OAUTH_CLIENT_ID_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv(GOOGLE_OAUTH_CLIENT_SECRET_ENV, "").strip()
    app.config["GOOGLE_OAUTH_CALLBACK_URL"] = os.getenv(GOOGLE_OAUTH_CALLBACK_URL_ENV, "").strip()
    app.config["EMAILS_BOOTSTRAP_ALLOWED_EMAILS"] = os.getenv(EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV, "").strip()
    app.config["EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS"] = os.getenv(EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV, "").strip()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["PREFERRED_URL_SCHEME"] = "https"

    if config:
        app.config.update(config)

    init_google_oauth(app)
    register_routes(app)
    return app


__all__ = ["create_app"]
