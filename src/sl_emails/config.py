from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .contracts.firestore_week_shape import EMAIL_WEEKS_COLLECTION


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"

SIGNAGE_OUTPUT_HTML = REPO_ROOT / "digital-signage" / "index.html"
SIGNAGE_TIMEZONE = "America/Denver"
SIGNAGE_ROLLOVER_GRACE_HOURS = 3
WEB_TEMPLATES_DIR = WEB_DIR / "templates"
WEB_STATIC_DIR = WEB_DIR / "static"

DEFAULT_FIRESTORE_DATABASE_ID = "(default)"

FIREBASE_PROJECT_ID_ENV = "FIREBASE_PROJECT_ID"
FIREBASE_SERVICE_ACCOUNT_JSON_ENV = "FIREBASE_SERVICE_ACCOUNT_JSON"
FIRESTORE_COLLECTION_ENV = "FIRESTORE_COLLECTION"
FIRESTORE_EMULATOR_HOST_ENV = "FIRESTORE_EMULATOR_HOST"
FIRESTORE_ACCESS_TOKEN_ENV = "FIRESTORE_ACCESS_TOKEN"
FIRESTORE_PROJECT_ID_ENV = "FIRESTORE_PROJECT_ID"
FIRESTORE_DATABASE_ID_ENV = "FIRESTORE_DATABASE_ID"
EMAILS_AUTOMATION_KEY_ENV = "EMAILS_AUTOMATION_KEY"
EMAILS_SESSION_SECRET_ENV = "EMAILS_SESSION_SECRET"
EMAILS_LOCAL_DEV_ENV = "EMAILS_LOCAL_DEV"
GOOGLE_OAUTH_CLIENT_ID_ENV = "GOOGLE_OAUTH_CLIENT_ID"
GOOGLE_OAUTH_CLIENT_SECRET_ENV = "GOOGLE_OAUTH_CLIENT_SECRET"
GOOGLE_OAUTH_CALLBACK_URL_ENV = "GOOGLE_OAUTH_CALLBACK_URL"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_ENV = "GEMINI_MODEL"
PUBLIC_BASE_URL_ENV = "PUBLIC_BASE_URL"
EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV = "EMAILS_BOOTSTRAP_ALLOWED_EMAILS"
EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV = "EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS"
GITHUB_RUN_ID_ENV = "GITHUB_RUN_ID"
GITHUB_SHA_ENV = "GITHUB_SHA"
GITHUB_WORKFLOW_ENV = "GITHUB_WORKFLOW"

EMAILS_SETTINGS_COLLECTION = "emailAdminSettings"
EMAILS_SETTINGS_DOC_ID = "sportsEmails"
EMAILS_ACTIVITY_COLLECTION = "emailActivityLog"
EMAILS_REQUESTS_SUBCOLLECTION = "eventRequests"


def _read_env(name: str) -> str:
    return os.getenv(name, "").strip()


@dataclass(frozen=True)
class RuntimeFirestoreConfig:
    collection_name: str = EMAIL_WEEKS_COLLECTION
    project_id: str | None = None
    service_account_json: str = ""
    emulator_host: str = ""

    @classmethod
    def from_env(cls, *, collection_name: str | None = None, project_id: str | None = None) -> "RuntimeFirestoreConfig":
        resolved_collection = collection_name or _read_env(FIRESTORE_COLLECTION_ENV) or EMAIL_WEEKS_COLLECTION
        resolved_project = project_id or _read_env(FIREBASE_PROJECT_ID_ENV) or None
        return cls(
            collection_name=resolved_collection,
            project_id=resolved_project,
            service_account_json=_read_env(FIREBASE_SERVICE_ACCOUNT_JSON_ENV),
            emulator_host=_read_env(FIRESTORE_EMULATOR_HOST_ENV),
        )


@dataclass(frozen=True)
class FirestoreDraftPublishConfig:
    project_id: str = ""
    access_token: str = ""
    database_id: str = DEFAULT_FIRESTORE_DATABASE_ID
    collection_name: str = EMAIL_WEEKS_COLLECTION
    github_run_id: str = ""
    github_sha: str = ""
    workflow: str = ""

    @classmethod
    def from_env(cls) -> "FirestoreDraftPublishConfig":
        return cls(
            project_id=_read_env(FIRESTORE_PROJECT_ID_ENV),
            access_token=_read_env(FIRESTORE_ACCESS_TOKEN_ENV),
            database_id=_read_env(FIRESTORE_DATABASE_ID_ENV) or DEFAULT_FIRESTORE_DATABASE_ID,
            collection_name=_read_env(FIRESTORE_COLLECTION_ENV) or EMAIL_WEEKS_COLLECTION,
            github_run_id=_read_env(GITHUB_RUN_ID_ENV),
            github_sha=_read_env(GITHUB_SHA_ENV),
            workflow=_read_env(GITHUB_WORKFLOW_ENV),
        )

    def missing(self) -> list[str]:
        missing: list[str] = []
        if not self.project_id:
            missing.append(FIRESTORE_PROJECT_ID_ENV)
        if not self.access_token:
            missing.append(FIRESTORE_ACCESS_TOKEN_ENV)
        return missing

    def run_context(self) -> dict[str, str]:
        return {
            "githubRunId": self.github_run_id,
            "githubSha": self.github_sha,
            "workflow": self.workflow,
        }


__all__ = [
    "DEFAULT_FIRESTORE_DATABASE_ID",
    "EMAILS_AUTOMATION_KEY_ENV",
    "EMAILS_BOOTSTRAP_ALLOWED_EMAILS_ENV",
    "EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS_ENV",
    "EMAILS_LOCAL_DEV_ENV",
    "EMAILS_SESSION_SECRET_ENV",
    "EMAILS_ACTIVITY_COLLECTION",
    "EMAILS_REQUESTS_SUBCOLLECTION",
    "EMAILS_SETTINGS_COLLECTION",
    "EMAILS_SETTINGS_DOC_ID",
    "FIREBASE_PROJECT_ID_ENV",
    "FIREBASE_SERVICE_ACCOUNT_JSON_ENV",
    "FIRESTORE_ACCESS_TOKEN_ENV",
    "FIRESTORE_COLLECTION_ENV",
    "FIRESTORE_DATABASE_ID_ENV",
    "FIRESTORE_EMULATOR_HOST_ENV",
    "FIRESTORE_PROJECT_ID_ENV",
    "FirestoreDraftPublishConfig",
    "GEMINI_API_KEY_ENV",
    "GEMINI_MODEL_ENV",
    "GOOGLE_OAUTH_CALLBACK_URL_ENV",
    "GOOGLE_OAUTH_CLIENT_ID_ENV",
    "GOOGLE_OAUTH_CLIENT_SECRET_ENV",
    "PACKAGE_DIR",
    "PUBLIC_BASE_URL_ENV",
    "REPO_ROOT",
    "RuntimeFirestoreConfig",
    "SIGNAGE_OUTPUT_HTML",
    "SIGNAGE_ROLLOVER_GRACE_HOURS",
    "SIGNAGE_TIMEZONE",
    "WEB_DIR",
    "WEB_STATIC_DIR",
    "WEB_TEMPLATES_DIR",
]
