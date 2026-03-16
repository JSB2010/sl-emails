from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
import re

from sl_emails.config import EMAILS_SETTINGS_COLLECTION, EMAILS_SETTINGS_DOC_ID
from sl_emails.domain.dates import utc_now_iso
from sl_emails.services.weekly_store import FirestoreWeeklyEmailStore


DEFAULT_ALLOWED_ADMIN_EMAILS = [
    "appdev@kentdenver.org",
    "studentleader@kentdenver.org",
]

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(value)))


def normalize_email_list(values: list[str] | tuple[str, ...] | set[str] | str | None) -> list[str]:
    if values is None:
        items: list[str] = []
    elif isinstance(values, str):
        items = re.split(r"[\s,;]+", values)
    else:
        items = [str(item) for item in values]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        email = normalize_email(item)
        if not email:
            continue
        if not is_valid_email(email):
            raise ValueError(f"Invalid email address: {item}")
        if email not in seen:
            seen.add(email)
            normalized.append(email)
    return normalized


@dataclass
class EmailAdminSettings:
    allowed_admin_emails: list[str]
    ops_notification_emails: list[str]
    sender_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    created_by: str = ""
    updated_at: str = ""
    updated_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EmailAdminSettings":
        data = dict(payload or {})
        return cls(
            allowed_admin_emails=normalize_email_list(data.get("allowed_admin_emails") or DEFAULT_ALLOWED_ADMIN_EMAILS),
            ops_notification_emails=normalize_email_list(data.get("ops_notification_emails") or DEFAULT_ALLOWED_ADMIN_EMAILS),
            sender_metadata=data.get("sender_metadata") if isinstance(data.get("sender_metadata"), dict) else {},
            created_at=str(data.get("created_at") or ""),
            created_by=str(data.get("created_by") or ""),
            updated_at=str(data.get("updated_at") or ""),
            updated_by=str(data.get("updated_by") or ""),
        )


class AdminSettingsStore(Protocol):
    def get_settings(self) -> EmailAdminSettings | None: ...

    def ensure_settings(self, *, allowed_admin_emails: list[str], ops_notification_emails: list[str], actor: str) -> EmailAdminSettings: ...

    def update_settings(
        self,
        *,
        allowed_admin_emails: list[str] | None = None,
        ops_notification_emails: list[str] | None = None,
        sender_metadata: dict[str, Any] | None = None,
        actor: str,
    ) -> EmailAdminSettings: ...


def _build_settings_payload(
    *,
    allowed_admin_emails: list[str],
    ops_notification_emails: list[str],
    existing: EmailAdminSettings | None,
    actor: str,
    sender_metadata: dict[str, Any] | None = None,
) -> EmailAdminSettings:
    normalized_admins = normalize_email_list(allowed_admin_emails)
    if not normalized_admins:
        raise ValueError("At least one allowed admin email is required")

    normalized_notifications = normalize_email_list(ops_notification_emails)
    if not normalized_notifications:
        raise ValueError("At least one ops notification email is required")

    timestamp = utc_now_iso()
    return EmailAdminSettings(
        allowed_admin_emails=normalized_admins,
        ops_notification_emails=normalized_notifications,
        sender_metadata=sender_metadata if isinstance(sender_metadata, dict) else (existing.sender_metadata if existing else {}),
        created_at=existing.created_at if existing else timestamp,
        created_by=existing.created_by if existing else actor,
        updated_at=timestamp,
        updated_by=actor,
    )


class MemoryAdminSettingsStore:
    def __init__(self) -> None:
        self._settings: EmailAdminSettings | None = None

    def get_settings(self) -> EmailAdminSettings | None:
        if self._settings is None:
            return None
        return EmailAdminSettings.from_dict(self._settings.to_dict())

    def ensure_settings(self, *, allowed_admin_emails: list[str], ops_notification_emails: list[str], actor: str) -> EmailAdminSettings:
        if self._settings is None:
            self._settings = _build_settings_payload(
                allowed_admin_emails=allowed_admin_emails,
                ops_notification_emails=ops_notification_emails,
                existing=None,
                actor=actor,
            )
        return self.get_settings()  # type: ignore[return-value]

    def update_settings(
        self,
        *,
        allowed_admin_emails: list[str] | None = None,
        ops_notification_emails: list[str] | None = None,
        sender_metadata: dict[str, Any] | None = None,
        actor: str,
    ) -> EmailAdminSettings:
        existing = self._settings or self.ensure_settings(
            allowed_admin_emails=DEFAULT_ALLOWED_ADMIN_EMAILS,
            ops_notification_emails=DEFAULT_ALLOWED_ADMIN_EMAILS,
            actor="bootstrap",
        )
        self._settings = _build_settings_payload(
            allowed_admin_emails=allowed_admin_emails if allowed_admin_emails is not None else existing.allowed_admin_emails,
            ops_notification_emails=ops_notification_emails if ops_notification_emails is not None else existing.ops_notification_emails,
            sender_metadata=sender_metadata,
            existing=existing,
            actor=actor,
        )
        return self.get_settings()  # type: ignore[return-value]


class FirestoreAdminSettingsStore:
    def __init__(self, *, collection_name: str = EMAILS_SETTINGS_COLLECTION, document_id: str = EMAILS_SETTINGS_DOC_ID) -> None:
        self.collection_name = collection_name
        self.document_id = document_id
        self._weekly_store = FirestoreWeeklyEmailStore()

    def _settings_ref(self):
        return self._weekly_store._get_client().collection(self.collection_name).document(self.document_id)

    def get_settings(self) -> EmailAdminSettings | None:
        snapshot = self._settings_ref().get()
        if not snapshot.exists:
            return None
        return EmailAdminSettings.from_dict(snapshot.to_dict() or {})

    def ensure_settings(self, *, allowed_admin_emails: list[str], ops_notification_emails: list[str], actor: str) -> EmailAdminSettings:
        existing = self.get_settings()
        if existing is not None:
            return existing
        settings = _build_settings_payload(
            allowed_admin_emails=allowed_admin_emails,
            ops_notification_emails=ops_notification_emails,
            existing=None,
            actor=actor,
        )
        self._settings_ref().set(settings.to_dict())
        return settings

    def update_settings(
        self,
        *,
        allowed_admin_emails: list[str] | None = None,
        ops_notification_emails: list[str] | None = None,
        sender_metadata: dict[str, Any] | None = None,
        actor: str,
    ) -> EmailAdminSettings:
        existing = self.get_settings()
        if existing is None:
            existing = self.ensure_settings(
                allowed_admin_emails=DEFAULT_ALLOWED_ADMIN_EMAILS,
                ops_notification_emails=DEFAULT_ALLOWED_ADMIN_EMAILS,
                actor="bootstrap",
            )
        settings = _build_settings_payload(
            allowed_admin_emails=allowed_admin_emails if allowed_admin_emails is not None else existing.allowed_admin_emails,
            ops_notification_emails=ops_notification_emails if ops_notification_emails is not None else existing.ops_notification_emails,
            sender_metadata=sender_metadata,
            existing=existing,
            actor=actor,
        )
        self._settings_ref().set(settings.to_dict())
        return settings


__all__ = [
    "AdminSettingsStore",
    "DEFAULT_ALLOWED_ADMIN_EMAILS",
    "EmailAdminSettings",
    "FirestoreAdminSettingsStore",
    "MemoryAdminSettingsStore",
    "is_valid_email",
    "normalize_email",
    "normalize_email_list",
]
