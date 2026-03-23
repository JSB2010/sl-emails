"""API routes for signage automation."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from sl_emails.services.signage_ingest import SignageRefreshResult, refresh_signage_day

from ..support import get_signage_store, json_error, require_automation_key


blueprint = Blueprint("signage_api", __name__, url_prefix="/api/signage")


def actor_for_request(default: str = "google-apps-script") -> str:
    actor = str(request.headers.get("X-Email-Actor") or default).strip()
    return actor or default


def serialize_refresh_result(result: SignageRefreshResult) -> Any:
    return jsonify(
        {
            "ok": True,
            "day_id": result.day_id,
            "action": result.action,
            "reason": result.reason,
            "source_summary": result.source_summary,
            "day": result.day.to_dict(),
        }
    )


@blueprint.post("/automation/days/<day_id>/refresh")
@require_automation_key
def refresh_day(day_id: str) -> Any:
    actor = actor_for_request()
    try:
        result = refresh_signage_day(get_signage_store(), day_id, actor=actor)
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return serialize_refresh_result(result)
