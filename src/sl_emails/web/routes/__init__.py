"""Route modules for the dedicated Flask web runtime package."""

from __future__ import annotations

from flask import Flask

from . import emails_api, emails_ui, poster_api, signage


def register_routes(app: Flask) -> None:
    app.register_blueprint(signage.blueprint)
    app.register_blueprint(emails_ui.blueprint)
    app.register_blueprint(poster_api.blueprint)
    app.register_blueprint(emails_api.blueprint)


__all__ = ["register_routes", "emails_api", "emails_ui", "poster_api", "signage"]