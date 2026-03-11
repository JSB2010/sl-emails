"""Application factory for the dedicated Flask web runtime package."""

from __future__ import annotations

from typing import Any

from flask import Flask

from .routes import register_routes
from .support import STATIC_DIR, TEMPLATE_DIR


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))

    if config:
        app.config.update(config)

    register_routes(app)
    return app


__all__ = ["create_app"]