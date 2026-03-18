from __future__ import annotations

from typing import Any, Protocol

from sl_emails.config import EMAILS_REQUESTS_SUBCOLLECTION
from sl_emails.domain.dates import iso_to_date, utc_now_iso
from sl_emails.domain.requests import EventRequestRecord, default_request_review, week_start_for_date
from sl_emails.domain.weekly import AUDIENCES, normalize_audiences
from sl_emails.services.admin_settings import is_valid_email, normalize_email
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore


REQUEST_STATUS_ORDER = {"pending": 0, "approved": 1, "denied": 2}


class EventRequestStore(Protocol):
    def list_requests(self, week_id: str) -> list[EventRequestRecord]: ...

    def get_request(self, week_id: str, request_id: str) -> EventRequestRecord | None: ...

    def submit_request(self, payload: dict[str, Any]) -> EventRequestRecord: ...

    def review_request(
        self,
        week_id: str,
        request_id: str,
        *,
        decision: str,
        reviewed_by: str,
        reviewer_notes: str = "",
        resolved_event_id: str = "",
    ) -> EventRequestRecord: ...


def _sort_requests(requests: list[EventRequestRecord]) -> list[EventRequestRecord]:
    return sorted(
        requests,
        key=lambda item: (
            REQUEST_STATUS_ORDER.get(item.status, 99),
            item.start_date,
            item.end_date,
            item.title.lower(),
            item.submitted_at,
        ),
    )


def normalize_request_payload(
    payload: dict[str, Any],
    *,
    existing: EventRequestRecord | None = None,
) -> EventRequestRecord:
    kind = str(payload.get("kind") or (existing.kind if existing else "event")).strip().lower() or "event"
    if kind not in {"event", "game"}:
        raise ValueError("Request kind must be 'event' or 'game'")

    start_date = str(payload.get("start_date") or payload.get("date") or (existing.start_date if existing else "")).strip()
    if not start_date:
        raise ValueError("Request start_date is required")
    end_date = str(payload.get("end_date") or (existing.end_date if existing else start_date)).strip() or start_date
    parsed_start = iso_to_date(start_date)
    parsed_end = iso_to_date(end_date)
    if parsed_end < parsed_start:
        raise ValueError("Request end_date must be on or after start_date")

    title = str(payload.get("title") or payload.get("team") or (existing.title if existing else "")).strip()
    if not title:
        raise ValueError("Request title is required")

    requester_name = str(payload.get("requester_name") or (existing.requester_name if existing else "")).strip()
    if not requester_name:
        raise ValueError("Requester name is required")

    requester_email = normalize_email(str(payload.get("requester_email") or (existing.requester_email if existing else "")).strip())
    if not requester_email:
        raise ValueError("Requester email is required")
    if not is_valid_email(requester_email):
        raise ValueError("Requester email must be valid")

    audiences = normalize_audiences(
        payload.get("audiences")
        or payload.get("audience")
        or (existing.audiences if existing else None)
    ) or list(AUDIENCES)
    week_id = str(payload.get("week_id") or (existing.week_id if existing else week_start_for_date(start_date))).strip() or week_start_for_date(start_date)
    timestamp = utc_now_iso()
    return EventRequestRecord(
        request_id=str(payload.get("request_id") or payload.get("id") or (existing.request_id if existing else "")).strip() or __import__("uuid").uuid4().hex,
        week_id=week_id,
        title=title,
        start_date=start_date,
        end_date=end_date,
        time_text=str(payload.get("time_text") or payload.get("time") or (existing.time_text if existing else "TBA")).strip() or "TBA",
        location=str(payload.get("location") or (existing.location if existing else "On Campus")).strip() or "On Campus",
        category=str(payload.get("category") or (existing.category if existing else "School Event")).strip() or "School Event",
        audiences=audiences,
        requester_name=requester_name,
        requester_email=requester_email,
        kind=kind,
        subtitle=str(payload.get("subtitle") or (existing.subtitle if existing else "")).strip(),
        description=str(payload.get("description") or (existing.description if existing else "")).strip(),
        link=str(payload.get("link") or (existing.link if existing else "")).strip(),
        requester_notes=str(payload.get("requester_notes") or payload.get("notes") or (existing.requester_notes if existing else "")).strip(),
        team=str(payload.get("team") or (existing.team if existing else title)).strip() or title,
        opponent=str(payload.get("opponent") or (existing.opponent if existing else "")).strip(),
        is_home=bool(payload.get("is_home", existing.is_home if existing else True)),
        status=existing.status if existing else "pending",
        review=dict(existing.review) if existing else default_request_review(),
        submitted_at=existing.submitted_at if existing else timestamp,
        updated_at=timestamp,
    )


def event_payload_for_request(record: EventRequestRecord) -> dict[str, Any]:
    return {
        "id": f"request-{record.request_id}",
        "title": record.title,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "time_text": record.time_text,
        "location": record.location,
        "category": record.category,
        "audiences": list(record.audiences),
        "kind": record.kind,
        "subtitle": record.subtitle,
        "description": record.description,
        "link": record.link,
        "team": record.team or record.title,
        "opponent": record.opponent,
        "is_home": record.is_home,
        "metadata": {
            "request_id": record.request_id,
            "requested_by_name": record.requester_name,
            "requested_by_email": record.requester_email,
            "requester_notes": record.requester_notes,
            "request_submitted_at": record.submitted_at,
        },
    }


class MemoryEventRequestStore:
    def __init__(self) -> None:
        self._requests: dict[str, dict[str, EventRequestRecord]] = {}

    def list_requests(self, week_id: str) -> list[EventRequestRecord]:
        items = list(self._requests.get(week_id, {}).values())
        return [EventRequestRecord.from_dict(item.to_dict()) for item in _sort_requests(items)]

    def get_request(self, week_id: str, request_id: str) -> EventRequestRecord | None:
        record = self._requests.get(week_id, {}).get(request_id)
        return EventRequestRecord.from_dict(record.to_dict()) if record is not None else None

    def submit_request(self, payload: dict[str, Any]) -> EventRequestRecord:
        record = normalize_request_payload(payload)
        self._requests.setdefault(record.week_id, {})[record.request_id] = record
        return self.get_request(record.week_id, record.request_id)  # type: ignore[return-value]

    def review_request(
        self,
        week_id: str,
        request_id: str,
        *,
        decision: str,
        reviewed_by: str,
        reviewer_notes: str = "",
        resolved_event_id: str = "",
    ) -> EventRequestRecord:
        record = self._requests.get(week_id, {}).get(request_id)
        if record is None:
            raise KeyError(request_id)
        if record.status != "pending":
            raise ValueError("Only pending requests can be reviewed")
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"approved", "denied"}:
            raise ValueError("decision must be one of: approved, denied")

        record.status = normalized_decision
        record.review = {
            "decision": normalized_decision,
            "reviewed_at": utc_now_iso(),
            "reviewed_by": str(reviewed_by or "").strip(),
            "reviewer_notes": str(reviewer_notes or "").strip(),
            "resolved_event_id": str(resolved_event_id or "").strip(),
        }
        record.updated_at = record.review["reviewed_at"]
        self._requests.setdefault(week_id, {})[request_id] = record
        return self.get_request(week_id, request_id)  # type: ignore[return-value]


class FirestoreEventRequestStore:
    def __init__(self, *, subcollection_name: str = EMAILS_REQUESTS_SUBCOLLECTION) -> None:
        self.subcollection_name = subcollection_name
        self._weekly_store = FirestoreWeeklyEmailStore()

    def _request_collection(self, week_id: str):
        return self._weekly_store._week_ref(week_id).collection(self.subcollection_name)

    def list_requests(self, week_id: str) -> list[EventRequestRecord]:
        items = [EventRequestRecord.from_dict(snapshot.to_dict() or {}) for snapshot in self._request_collection(week_id).stream()]
        return _sort_requests(items)

    def get_request(self, week_id: str, request_id: str) -> EventRequestRecord | None:
        snapshot = self._request_collection(week_id).document(request_id).get()
        if not snapshot.exists:
            return None
        return EventRequestRecord.from_dict(snapshot.to_dict() or {})

    def submit_request(self, payload: dict[str, Any]) -> EventRequestRecord:
        record = normalize_request_payload(payload)
        self._request_collection(record.week_id).document(record.request_id).set(record.to_firestore())
        return self.get_request(record.week_id, record.request_id)  # type: ignore[return-value]

    def review_request(
        self,
        week_id: str,
        request_id: str,
        *,
        decision: str,
        reviewed_by: str,
        reviewer_notes: str = "",
        resolved_event_id: str = "",
    ) -> EventRequestRecord:
        record = self.get_request(week_id, request_id)
        if record is None:
            raise KeyError(request_id)
        if record.status != "pending":
            raise ValueError("Only pending requests can be reviewed")
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"approved", "denied"}:
            raise ValueError("decision must be one of: approved, denied")

        reviewed_at = utc_now_iso()
        patch = {
            "status": normalized_decision,
            "review": {
                "decision": normalized_decision,
                "reviewed_at": reviewed_at,
                "reviewed_by": str(reviewed_by or "").strip(),
                "reviewer_notes": str(reviewer_notes or "").strip(),
                "resolved_event_id": str(resolved_event_id or "").strip(),
            },
            "updated_at": reviewed_at,
        }
        self._request_collection(week_id).document(request_id).set(patch, merge=True)
        return self.get_request(week_id, request_id)  # type: ignore[return-value]


__all__ = [
    "EventRequestStore",
    "FirestoreEventRequestStore",
    "MemoryEventRequestStore",
    "event_payload_for_request",
    "normalize_request_payload",
]
