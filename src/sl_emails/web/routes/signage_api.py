"""API routes for signage automation."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from sl_emails.services.signage_ingest import SignageRefreshResult, SignageSourceFetchError, refresh_signage_day

from ..support import get_signage_store, is_local_dev_or_testing, json_error, require_automation_key, update_signage_metadata_safely, write_activity


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
            "source_health": result.source_health,
            "day": result.day.to_dict(),
        }
    )


@blueprint.post("/automation/days/<day_id>/refresh")
@require_automation_key
def refresh_day(day_id: str) -> Any:
    actor = actor_for_request()
    try:
        result = refresh_signage_day(get_signage_store(), day_id, actor=actor)
    except SignageSourceFetchError as exc:
        update_signage_metadata_safely(
            day_id,
            {
                "ingest": {
                    "status": "failed",
                    "actor": actor,
                    "message": str(exc),
                    "occurred_at": "",
                    "source_health": exc.source_health,
                }
            },
        )
        write_activity(
            event_type="signage_refresh",
            status="failed",
            actor=actor,
            message=str(exc),
            details={"day_id": day_id, "source_health": exc.source_health},
        )
        return json_error(str(exc), status=503, extra={"source_health": exc.source_health})
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    write_activity(
        event_type="signage_refresh",
        status="success",
        actor=actor,
        message=f"Signage refresh {result.action}",
        details={"day_id": day_id, "source_summary": result.source_summary, "source_health": result.source_health},
    )
    return serialize_refresh_result(result)


@blueprint.post("/local/days/<day_id>/refresh")
def refresh_day_local(day_id: str) -> Any:
    if not is_local_dev_or_testing():
        return json_error("Local signage refresh is only available in local dev.", status=404)

    actor = actor_for_request(default="local-dev")
    try:
        result = refresh_signage_day(get_signage_store(), day_id, actor=actor)
    except SignageSourceFetchError as exc:
        update_signage_metadata_safely(
            day_id,
            {
                "ingest": {
                    "status": "failed",
                    "actor": actor,
                    "message": str(exc),
                    "occurred_at": "",
                    "source_health": exc.source_health,
                }
            },
        )
        return json_error(str(exc), status=503, extra={"source_health": exc.source_health})
    except ValueError as exc:
        return json_error(str(exc), status=400)
    except RuntimeError as exc:
        return json_error(str(exc), status=503)

    return serialize_refresh_result(result)
