#!/usr/bin/env python3
"""Helpers for publishing weekly email draft data to Firestore via REST."""

from __future__ import annotations

from typing import Any

import requests

from sl_emails.contracts.firestore_week_shape import (
    EMAIL_WEEKS_COLLECTION,
    EVENTS_SUBCOLLECTION,
    build_week_draft_document,
)
from sl_emails.domain.weekly import DEFAULT_HEADING


def _to_firestore_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {key: _to_firestore_value(nested) for key, nested in value.items()}}}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [_to_firestore_value(item) for item in value]}}
    raise TypeError(f"Unsupported Firestore value type: {type(value)!r}")


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _patch_document(*, document_name: str, payload: dict[str, Any], access_token: str) -> None:
    params = [("updateMask.fieldPaths", key) for key in payload.keys()]
    response = requests.patch(
        f"https://firestore.googleapis.com/v1/{document_name}",
        headers=_headers(access_token),
        params=params,
        json={
            "name": document_name,
            "fields": {key: _to_firestore_value(value) for key, value in payload.items()},
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Firestore draft upsert failed ({response.status_code}): {response.text}")
    response.raise_for_status()


def _list_existing_event_ids(*, parent_document_name: str, access_token: str) -> set[str]:
    event_ids: set[str] = set()
    page_token = ""

    while True:
        params: dict[str, Any] = {"pageSize": 500}
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            f"https://firestore.googleapis.com/v1/{parent_document_name}/{EVENTS_SUBCOLLECTION}",
            headers=_headers(access_token),
            params=params,
            timeout=30,
        )
        if response.status_code == 404:
            return event_ids
        if not response.ok:
            raise RuntimeError(f"Firestore event listing failed ({response.status_code}): {response.text}")

        payload = response.json()
        for document in payload.get("documents", []):
            name = str(document.get("name", "")).strip()
            if name:
                event_ids.add(name.rsplit("/", 1)[-1])

        page_token = str(payload.get("nextPageToken", "")).strip()
        if not page_token:
            return event_ids


def _delete_document(*, document_name: str, access_token: str) -> None:
    response = requests.delete(
        f"https://firestore.googleapis.com/v1/{document_name}",
        headers=_headers(access_token),
        timeout=30,
    )
    if response.status_code == 404:
        return
    if not response.ok:
        raise RuntimeError(f"Firestore draft delete failed ({response.status_code}): {response.text}")


def upsert_week_draft(
    *,
    document: dict[str, Any],
    access_token: str,
    project_id: str,
    database_id: str = "(default)",
    collection: str = EMAIL_WEEKS_COLLECTION,
) -> str:
    if not access_token.strip():
        raise ValueError("FIRESTORE_ACCESS_TOKEN is required for Firestore draft publishing")
    if not project_id.strip():
        raise ValueError("FIRESTORE_PROJECT_ID is required for Firestore draft publishing")

    document_name = f"projects/{project_id}/databases/{database_id}/documents/{collection}/{document['weekKey']}"
    week_payload = document.get("week") if isinstance(document.get("week"), dict) else {}
    events_payload = document.get("events") if isinstance(document.get("events"), list) else []

    _patch_document(document_name=document_name, payload=week_payload, access_token=access_token)

    existing_event_ids = _list_existing_event_ids(parent_document_name=document_name, access_token=access_token)
    incoming_event_ids = set()
    for event in events_payload:
        event_id = str(event.get("id", "")).strip()
        if not event_id:
            continue
        incoming_event_ids.add(event_id)
        _patch_document(
            document_name=f"{document_name}/{EVENTS_SUBCOLLECTION}/{event_id}",
            payload=event,
            access_token=access_token,
        )

    for stale_event_id in existing_event_ids - incoming_event_ids:
        _delete_document(
            document_name=f"{document_name}/{EVENTS_SUBCOLLECTION}/{stale_event_id}",
            access_token=access_token,
        )

    return document_name


__all__ = ["DEFAULT_HEADING", "build_week_draft_document", "upsert_week_draft"]