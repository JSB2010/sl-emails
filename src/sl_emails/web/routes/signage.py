"""Routes for the signage-facing runtime surface."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify

from ..support import serve_signage


blueprint = Blueprint("signage", __name__)


@blueprint.get("/")
def root():
    return Response("OK", status=200, mimetype="text/plain")


@blueprint.get("/signage")
def index():
    return serve_signage()


@blueprint.get("/_health")
@blueprint.get("/healthz")
def healthcheck() -> Response:
    return jsonify({"ok": True})
