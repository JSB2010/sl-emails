from __future__ import annotations

from typing import Any, Protocol
import json

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    credentials = None
    firestore = None

try:
    from google.api_core.exceptions import AlreadyExists
except ImportError:  # pragma: no cover
    class AlreadyExists(Exception):
        """Fallback exception when google-api-core is unavailable."""

from ..contracts.firestore_week_shape import EMAIL_WEEKS_COLLECTION, EVENTS_SUBCOLLECTION
from ..config import RuntimeFirestoreConfig
from ..domain.dates import iso_to_date, time_sort_key, utc_now_iso, week_end_for, week_start_for
from ..domain.iconography import normalize_icon_key
from ..domain.styling import SOURCE_ACCENTS
from ..domain.weekly import (
    DEFAULT_HEADING,
    DEFAULT_STATUS,
    WeeklyDraftRecord,
    WeeklyEventRecord,
    default_audience_copy_overrides,
    default_copy_overrides,
    default_delivery_state,
    default_sent_state,
    default_approval_state,
    infer_audiences,
    normalize_audience_copy_overrides,
    normalize_copy_overrides,
    normalize_delivery,
    normalize_sent_state,
    normalize_subject_overrides,
)


class WeeklyEmailStore(Protocol):
    def get_week(self, week_id: str) -> WeeklyDraftRecord | None: ...

    def create_week_if_missing(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord | None: ...

    def save_week(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord: ...

    def add_event(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord: ...

    def approve_week(self, week_id: str, approved_by: str = "open-access") -> WeeklyDraftRecord: ...

    def claim_week_send(self, week_id: str, sending_by: str = "open-access") -> WeeklyDraftRecord: ...

    def mark_week_sent(self, week_id: str, sent_by: str = "open-access") -> WeeklyDraftRecord: ...

    def reset_week_send(self, week_id: str) -> WeeklyDraftRecord: ...

    def update_week_metadata(self, week_id: str, metadata: dict[str, Any]) -> WeeklyDraftRecord: ...


def merge_metadata(base: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(base or {})
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_metadata(result.get(key), value)
        else:
            result[key] = value
    return result


def is_send_locked(sent_state: Any) -> bool:
    normalized = normalize_sent_state(sent_state)
    return bool(normalized.get("sent") or normalized.get("sending"))


def assert_week_editable(existing: WeeklyDraftRecord | None) -> None:
    if existing is None:
        return
    if is_send_locked(existing.sent):
        raise ValueError("Week is locked for sending. Mark it unsent before editing the draft.")


def normalize_event_payload(
    payload: dict[str, Any],
    *,
    week_start: str,
    week_end: str,
    force_source: str | None = None,
) -> WeeklyEventRecord:
    source = str(force_source or payload.get("source") or "custom").strip().lower() or "custom"
    kind = str(payload.get("kind") or ("game" if payload.get("team") or payload.get("opponent") else "event")).strip().lower()
    if kind not in {"game", "event"}:
        raise ValueError("Event kind must be 'game' or 'event'")

    start_date = str(payload.get("start_date") or payload.get("date") or "").strip()
    if not start_date:
        raise ValueError("Event start_date is required")
    end_date = str(payload.get("end_date") or start_date).strip() or start_date
    parsed_start = iso_to_date(start_date)
    parsed_end = iso_to_date(end_date)
    if parsed_end < parsed_start:
        raise ValueError("Event end_date must be on or after start_date")
    if parsed_end < iso_to_date(week_start) or parsed_start > iso_to_date(week_end):
        raise ValueError("Event must overlap the requested week")

    team = str(payload.get("team") or "").strip()
    opponent = str(payload.get("opponent") or "").strip()
    title = str(payload.get("title") or team or "").strip()
    if not title:
        raise ValueError("Event title is required")

    badge_default = "SPECIAL" if source == "custom" else ("HOME" if bool(payload.get("is_home", True)) else "AWAY")
    accent_default = SOURCE_ACCENTS.get(source, SOURCE_ACCENTS["custom"])
    subtitle_default = f"vs. {opponent}" if kind == "game" and opponent else str(payload.get("category", "School Event"))
    timestamp = utc_now_iso()
    return WeeklyEventRecord(
        id=str(payload.get("id") or __import__("uuid").uuid4().hex).strip(),
        title=title,
        start_date=start_date,
        end_date=end_date,
        time_text=str(payload.get("time_text") or payload.get("time") or "TBA").strip() or "TBA",
        location=str(payload.get("location", "On Campus")).strip() or "On Campus",
        category=str(payload.get("category", "School Event")).strip() or "School Event",
        source=source,
        audiences=infer_audiences(payload, source=source),
        kind=kind,
        subtitle=str(payload.get("subtitle") or subtitle_default).strip(),
        description=str(payload.get("description", "")).strip(),
        link=str(payload.get("link", "")).strip(),
        icon=normalize_icon_key(str(payload.get("icon", "")).strip()),
        badge=str(payload.get("badge") or badge_default).strip().upper() or badge_default,
        priority=max(1, min(int(payload.get("priority", 3)), 5)),
        accent=str(payload.get("accent") or accent_default).strip() or accent_default,
        source_id=str(payload.get("source_id", "")).strip(),
        status=str(payload.get("status", "active")).strip() or "active",
        team=team or title,
        opponent=opponent,
        is_home=bool(payload.get("is_home", True)),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        created_at=str(payload.get("created_at") or timestamp).strip(),
        updated_at=timestamp,
    )


def normalize_week_payload(
    week_id: str,
    payload: dict[str, Any],
    *,
    existing: WeeklyDraftRecord | None = None,
) -> WeeklyDraftRecord:
    canonical_week_id = week_start_for(week_id)
    start_value = payload["start_date"] if "start_date" in payload else (existing.start_date if existing else canonical_week_id)
    start_date = week_start_for(str(start_value or canonical_week_id).strip() or canonical_week_id)
    end_value = payload["end_date"] if "end_date" in payload else (existing.end_date if existing else week_end_for(start_date))
    end_date = str(end_value or week_end_for(start_date)).strip() or week_end_for(start_date)
    if canonical_week_id != start_date:
        raise ValueError("week_id must match the week start_date")
    if iso_to_date(end_date) < iso_to_date(start_date):
        raise ValueError("Week end_date must be on or after start_date")

    events_payload = payload.get("events")
    if events_payload is None and existing is not None:
        events_payload = [event.to_dict() for event in existing.events]
    elif events_payload is None:
        events_payload = []
    if not isinstance(events_payload, list):
        raise ValueError("events must be an array")

    events = [
        normalize_event_payload(item, week_start=start_date, week_end=end_date)
        for item in events_payload
        if isinstance(item, dict)
    ]
    events.sort(key=lambda event: (event.start_date, event.end_date, time_sort_key(event.time_text), event.title.lower()))
    timestamp = utc_now_iso()
    existing_delivery = existing.delivery if existing else default_delivery_state(start_date)
    next_delivery = normalize_delivery(
        payload.get("delivery"),
        week_id=start_date,
        fallback=existing_delivery,
    )
    next_delivery["updated_at"] = timestamp
    next_delivery["updated_by"] = str((payload.get("delivery") or {}).get("updated_by") or next_delivery.get("updated_by") or "").strip()
    heading_value = payload["heading"] if "heading" in payload else (existing.heading if existing else DEFAULT_HEADING)
    notes_value = payload["notes"] if "notes" in payload else (existing.notes if existing else "")
    copy_overrides = normalize_copy_overrides(
        payload.get("copy_overrides")
        if isinstance(payload.get("copy_overrides"), dict)
        else (existing.copy_overrides if existing else default_copy_overrides())
    )
    if isinstance(payload.get("copy_overrides_by_audience"), dict):
        audience_copy_payload: Any = payload.get("copy_overrides_by_audience")
    elif "copy_overrides" in payload:
        audience_copy_payload = {}
    else:
        audience_copy_payload = existing.copy_overrides_by_audience if existing else {}
    return WeeklyDraftRecord(
        week_id=canonical_week_id,
        start_date=start_date,
        end_date=end_date,
        heading=str(heading_value or DEFAULT_HEADING).strip() or DEFAULT_HEADING,
        status=DEFAULT_STATUS,
        approval=default_approval_state(),
        sent=default_sent_state(),
        notes=str(notes_value or "").strip(),
        subject_overrides=normalize_subject_overrides(
            payload.get("subject_overrides")
            if isinstance(payload.get("subject_overrides"), dict)
            else (existing.subject_overrides if existing else {})
        ),
        delivery=next_delivery,
        copy_overrides=copy_overrides,
        copy_overrides_by_audience=normalize_audience_copy_overrides(
            audience_copy_payload,
            fallback=copy_overrides,
        ),
        events=events,
        metadata=merge_metadata(existing.metadata if existing else {}, payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
        created_at=existing.created_at if existing else timestamp,
        updated_at=timestamp,
    )


def build_blank_week_payload(week_id: str) -> dict[str, Any]:
    start_date = week_start_for(week_id)
    return {
        "start_date": start_date,
        "end_date": week_end_for(start_date),
        "heading": DEFAULT_HEADING,
        "notes": "",
        "subject_overrides": {},
        "delivery": default_delivery_state(start_date),
        "copy_overrides": default_copy_overrides(),
        "copy_overrides_by_audience": default_audience_copy_overrides(),
        "events": [],
    }


class MemoryWeeklyEmailStore:
    def __init__(self) -> None:
        self._weeks: dict[str, WeeklyDraftRecord] = {}

    def get_week(self, week_id: str) -> WeeklyDraftRecord | None:
        week = self._weeks.get(week_start_for(week_id))
        if week is None:
            return None
        return WeeklyDraftRecord(
            week_id=week.week_id,
            start_date=week.start_date,
            end_date=week.end_date,
            heading=week.heading,
            status=week.status,
            approval=dict(week.approval),
            sent=normalize_sent_state(week.sent),
            notes=week.notes,
            subject_overrides=dict(week.subject_overrides),
            delivery=dict(week.delivery),
            copy_overrides=dict(week.copy_overrides),
            copy_overrides_by_audience={audience: dict(copy) for audience, copy in week.copy_overrides_by_audience.items()},
            events=[WeeklyEventRecord.from_dict(event.to_dict()) for event in week.events],
            metadata=dict(week.metadata),
            created_at=week.created_at,
            updated_at=week.updated_at,
        )

    def create_week_if_missing(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord | None:
        canonical_week_id = week_start_for(week_id)
        if canonical_week_id in self._weeks:
            return None
        week = normalize_week_payload(canonical_week_id, payload)
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def save_week(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        existing = self._weeks.get(canonical_week_id)
        assert_week_editable(existing)
        week = normalize_week_payload(canonical_week_id, payload, existing=existing)
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def add_event(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        existing = self._weeks.get(canonical_week_id)
        base_payload = existing.to_dict() if existing else build_blank_week_payload(canonical_week_id)
        events = list(base_payload.get("events", []))
        events.append(normalize_event_payload(payload, week_start=base_payload["start_date"], week_end=base_payload["end_date"], force_source="custom").to_dict())
        base_payload["events"] = events
        return self.save_week(canonical_week_id, base_payload)

    def approve_week(self, week_id: str, approved_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        week = self._weeks.get(canonical_week_id)
        if week is None:
            raise KeyError(canonical_week_id)
        if is_send_locked(week.sent):
            raise ValueError("Week is locked for sending. Mark it unsent before approving again.")
        if str((week.delivery or {}).get("mode") or "").strip().lower() == "skip":
            raise ValueError("Weeks marked “No email this week” cannot be approved until delivery is changed.")
        timestamp = utc_now_iso()
        week.status = "approved"
        week.approval = {"approved": True, "approved_at": timestamp, "approved_by": approved_by}
        week.updated_at = timestamp
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def claim_week_send(self, week_id: str, sending_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        week = self._weeks.get(canonical_week_id)
        if week is None:
            raise KeyError(canonical_week_id)
        if not week.approval.get("approved"):
            raise ValueError("Week must be approved before it can be claimed for sending")
        sent_state = normalize_sent_state(week.sent)
        if sent_state.get("sent"):
            return self.get_week(canonical_week_id)  # type: ignore[return-value]
        if sent_state.get("sending"):
            raise ValueError(
                f"Week is already claimed for sending by {sent_state.get('sending_by') or 'unknown actor'} "
                f"at {sent_state.get('sending_at') or 'unknown time'}"
            )
        timestamp = utc_now_iso()
        week.sent = {"sent": False, "sent_at": "", "sent_by": "", "sending": True, "sending_at": timestamp, "sending_by": sending_by}
        week.updated_at = timestamp
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def mark_week_sent(self, week_id: str, sent_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        week = self._weeks.get(canonical_week_id)
        if week is None:
            raise KeyError(canonical_week_id)
        if not week.approval.get("approved"):
            raise ValueError("Week must be approved before it can be marked sent")
        sent_state = normalize_sent_state(week.sent)
        if sent_state.get("sent"):
            return self.get_week(canonical_week_id)  # type: ignore[return-value]
        if not sent_state.get("sending"):
            raise ValueError("Week must be claimed for sending before it can be marked sent")
        timestamp = utc_now_iso()
        week.sent = {"sent": True, "sent_at": timestamp, "sent_by": sent_by, "sending": False, "sending_at": "", "sending_by": ""}
        week.updated_at = timestamp
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def reset_week_send(self, week_id: str) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        week = self._weeks.get(canonical_week_id)
        if week is None:
            raise KeyError(canonical_week_id)
        sent_state = normalize_sent_state(week.sent)
        if not sent_state.get("sent") and not sent_state.get("sending"):
            return self.get_week(canonical_week_id)  # type: ignore[return-value]
        week.sent = default_sent_state()
        week.updated_at = utc_now_iso()
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def update_week_metadata(self, week_id: str, metadata: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        week = self._weeks.get(canonical_week_id)
        if week is None:
            raise KeyError(canonical_week_id)
        week.metadata = merge_metadata(week.metadata, metadata)
        week.updated_at = utc_now_iso()
        self._weeks[canonical_week_id] = week
        return self.get_week(canonical_week_id)  # type: ignore[return-value]


class FirestoreWeeklyEmailStore:
    def __init__(
        self,
        *,
        collection_name: str | None = None,
        project_id: str | None = None,
        runtime_config: RuntimeFirestoreConfig | None = None,
    ) -> None:
        self.runtime_config = runtime_config or RuntimeFirestoreConfig.from_env(
            collection_name=collection_name,
            project_id=project_id,
        )
        self.collection_name = self.runtime_config.collection_name or EMAIL_WEEKS_COLLECTION
        self.project_id = self.runtime_config.project_id
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if firebase_admin is None or firestore is None:
            raise RuntimeError("firebase_admin is not available. Install Firebase Admin SDK to use Firestore storage.")
        if not firebase_admin._apps:
            options = {"projectId": self.project_id} if self.project_id else None
            service_account_json = self.runtime_config.service_account_json
            if self.runtime_config.emulator_host and not service_account_json:
                firebase_admin.initialize_app(options=options)
            elif service_account_json:
                credential = credentials.Certificate(json.loads(service_account_json))
                firebase_admin.initialize_app(credential=credential, options=options)
            else:
                credential = credentials.ApplicationDefault()
                firebase_admin.initialize_app(credential=credential, options=options)
        self._client = firestore.client()
        return self._client

    def _week_ref(self, week_id: str):
        return self._get_client().collection(self.collection_name).document(week_id)

    def _week_snapshot(self, week_id: str, *, transaction: Any | None = None):
        week_ref = self._week_ref(week_id)
        if transaction is None:
            return week_ref.get()
        return week_ref.get(transaction=transaction)

    def get_week(self, week_id: str) -> WeeklyDraftRecord | None:
        canonical_week_id = week_start_for(week_id)
        week_ref = self._week_ref(canonical_week_id)
        snapshot = self._week_snapshot(canonical_week_id)
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        events = [WeeklyEventRecord.from_dict(item.to_dict() or {}) for item in week_ref.collection(EVENTS_SUBCOLLECTION).stream()]
        events.sort(key=lambda event: (event.start_date, event.end_date, time_sort_key(event.time_text), event.title.lower()))
        return WeeklyDraftRecord(
            week_id=canonical_week_id,
            start_date=week_start_for(str(data.get("start_date") or canonical_week_id)),
            end_date=str(data.get("end_date") or week_end_for(canonical_week_id)),
            heading=str(data.get("heading") or DEFAULT_HEADING),
            status=str(data.get("status") or DEFAULT_STATUS),
            approval=data.get("approval") if isinstance(data.get("approval"), dict) else default_approval_state(),
            sent=normalize_sent_state(data.get("sent")),
            notes=str(data.get("notes") or ""),
            subject_overrides=normalize_subject_overrides(data.get("subject_overrides")),
            delivery=normalize_delivery(data.get("delivery"), week_id=canonical_week_id),
            copy_overrides=normalize_copy_overrides(data.get("copy_overrides")),
            copy_overrides_by_audience=normalize_audience_copy_overrides(data.get("copy_overrides_by_audience"), fallback=data.get("copy_overrides")),
            events=events,
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )

    def create_week_if_missing(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord | None:
        canonical_week_id = week_start_for(week_id)
        week = normalize_week_payload(canonical_week_id, payload)
        week_ref = self._week_ref(canonical_week_id)
        batch = self._get_client().batch()
        batch.create(week_ref, week.to_firestore())
        for event in week.events:
            batch.set(week_ref.collection(EVENTS_SUBCOLLECTION).document(event.id), event.to_firestore())
        try:
            batch.commit()
        except AlreadyExists:
            return None
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def save_week(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        existing = self.get_week(canonical_week_id)
        assert_week_editable(existing)
        week = normalize_week_payload(canonical_week_id, payload, existing=existing)
        week_ref = self._week_ref(canonical_week_id)
        current_ids = {item.id for item in (existing.events if existing else [])}
        incoming_ids = {event.id for event in week.events}
        batch = self._get_client().batch()
        batch.set(week_ref, week.to_firestore())
        for stale_id in current_ids - incoming_ids:
            batch.delete(week_ref.collection(EVENTS_SUBCOLLECTION).document(stale_id))
        for event in week.events:
            batch.set(week_ref.collection(EVENTS_SUBCOLLECTION).document(event.id), event.to_firestore())
        batch.commit()
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def add_event(self, week_id: str, payload: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        existing = self.get_week(canonical_week_id)
        base_payload = existing.to_dict() if existing else build_blank_week_payload(canonical_week_id)
        events = list(base_payload.get("events", []))
        events.append(normalize_event_payload(payload, week_start=base_payload["start_date"], week_end=base_payload["end_date"], force_source="custom").to_dict())
        base_payload["events"] = events
        return self.save_week(canonical_week_id, base_payload)

    def approve_week(self, week_id: str, approved_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        transaction = self._get_client().transaction()
        week_ref = self._week_ref(canonical_week_id)

        @firestore.transactional
        def apply(transaction: Any) -> None:
            snapshot = self._week_snapshot(canonical_week_id, transaction=transaction)
            if not snapshot.exists:
                raise KeyError(canonical_week_id)
            data = snapshot.to_dict() or {}
            if is_send_locked(data.get("sent")):
                raise ValueError("Week is locked for sending. Mark it unsent before approving again.")
            delivery = data.get("delivery") if isinstance(data.get("delivery"), dict) else {}
            if str(delivery.get("mode") or "").strip().lower() == "skip":
                raise ValueError("Weeks marked “No email this week” cannot be approved until delivery is changed.")
            timestamp = utc_now_iso()
            transaction.set(
                week_ref,
                {
                    "status": "approved",
                    "approval": {"approved": True, "approved_at": timestamp, "approved_by": approved_by},
                    "updated_at": timestamp,
                },
                merge=True,
            )

        apply(transaction)
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def claim_week_send(self, week_id: str, sending_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        transaction = self._get_client().transaction()
        week_ref = self._week_ref(canonical_week_id)

        @firestore.transactional
        def apply(transaction: Any) -> None:
            snapshot = self._week_snapshot(canonical_week_id, transaction=transaction)
            if not snapshot.exists:
                raise KeyError(canonical_week_id)
            data = snapshot.to_dict() or {}
            approval = data.get("approval") if isinstance(data.get("approval"), dict) else default_approval_state()
            if not approval.get("approved"):
                raise ValueError("Week must be approved before it can be claimed for sending")
            sent_state = normalize_sent_state(data.get("sent"))
            if sent_state.get("sent"):
                return
            if sent_state.get("sending"):
                raise ValueError(
                    f"Week is already claimed for sending by {sent_state.get('sending_by') or 'unknown actor'} "
                    f"at {sent_state.get('sending_at') or 'unknown time'}"
                )
            timestamp = utc_now_iso()
            transaction.set(
                week_ref,
                {
                    "sent": {
                        "sent": False,
                        "sent_at": "",
                        "sent_by": "",
                        "sending": True,
                        "sending_at": timestamp,
                        "sending_by": sending_by,
                    },
                    "updated_at": timestamp,
                },
                merge=True,
            )

        apply(transaction)
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def mark_week_sent(self, week_id: str, sent_by: str = "open-access") -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        transaction = self._get_client().transaction()
        week_ref = self._week_ref(canonical_week_id)

        @firestore.transactional
        def apply(transaction: Any) -> None:
            snapshot = self._week_snapshot(canonical_week_id, transaction=transaction)
            if not snapshot.exists:
                raise KeyError(canonical_week_id)
            data = snapshot.to_dict() or {}
            approval = data.get("approval") if isinstance(data.get("approval"), dict) else default_approval_state()
            if not approval.get("approved"):
                raise ValueError("Week must be approved before it can be marked sent")
            sent_state = normalize_sent_state(data.get("sent"))
            if sent_state.get("sent"):
                return
            if not sent_state.get("sending"):
                raise ValueError("Week must be claimed for sending before it can be marked sent")
            timestamp = utc_now_iso()
            transaction.set(
                week_ref,
                {
                    "sent": {
                        "sent": True,
                        "sent_at": timestamp,
                        "sent_by": sent_by,
                        "sending": False,
                        "sending_at": "",
                        "sending_by": "",
                    },
                    "updated_at": timestamp,
                },
                merge=True,
            )

        apply(transaction)
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def reset_week_send(self, week_id: str) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        transaction = self._get_client().transaction()
        week_ref = self._week_ref(canonical_week_id)

        @firestore.transactional
        def apply(transaction: Any) -> None:
            snapshot = self._week_snapshot(canonical_week_id, transaction=transaction)
            if not snapshot.exists:
                raise KeyError(canonical_week_id)
            timestamp = utc_now_iso()
            transaction.set(week_ref, {"sent": default_sent_state(), "updated_at": timestamp}, merge=True)

        apply(transaction)
        return self.get_week(canonical_week_id)  # type: ignore[return-value]

    def update_week_metadata(self, week_id: str, metadata: dict[str, Any]) -> WeeklyDraftRecord:
        canonical_week_id = week_start_for(week_id)
        transaction = self._get_client().transaction()
        week_ref = self._week_ref(canonical_week_id)

        @firestore.transactional
        def apply(transaction: Any) -> None:
            snapshot = self._week_snapshot(canonical_week_id, transaction=transaction)
            if not snapshot.exists:
                raise KeyError(canonical_week_id)
            data = snapshot.to_dict() or {}
            merged = merge_metadata(data.get("metadata") if isinstance(data.get("metadata"), dict) else {}, metadata)
            timestamp = utc_now_iso()
            transaction.set(week_ref, {"metadata": merged, "updated_at": timestamp}, merge=True)

        apply(transaction)
        return self.get_week(canonical_week_id)  # type: ignore[return-value]
