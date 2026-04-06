from __future__ import annotations

from typing import Any


ICON_STATIC_PREFIX = "/static/icons"

ICON_REGISTRY: dict[str, dict[str, str]] = {
    "soccer": {"label": "Soccer", "filename": "soccer.svg"},
    "football": {"label": "Football", "filename": "football.svg"},
    "basketball": {"label": "Basketball", "filename": "basketball.svg"},
    "baseball": {"label": "Baseball", "filename": "baseball.svg"},
    "lacrosse": {"label": "Lacrosse", "filename": "lacrosse.svg"},
    "golf": {"label": "Golf", "filename": "golf.svg"},
    "volleyball": {"label": "Volleyball", "filename": "volleyball.svg"},
    "hockey": {"label": "Hockey", "filename": "hockey.svg"},
    "swimming": {"label": "Swimming", "filename": "swimming.svg"},
    "running": {"label": "Running", "filename": "running.svg"},
    "tennis": {"label": "Tennis", "filename": "tennis.svg"},
    "competition": {"label": "Competition", "filename": "competition.svg"},
    "medal": {"label": "Medal", "filename": "medal.svg"},
    "trophy": {"label": "Trophy", "filename": "trophy.svg"},
    "music": {"label": "Music", "filename": "music.svg"},
    "performance": {"label": "Performance", "filename": "performance.svg"},
    "theater": {"label": "Theater", "filename": "theater.svg"},
    "visual-arts": {"label": "Visual Arts", "filename": "visual-arts.svg"},
    "camera": {"label": "Photo / Media", "filename": "camera.svg"},
    "showcase": {"label": "Showcase", "filename": "showcase.svg"},
    "calendar": {"label": "Calendar", "filename": "calendar.svg"},
    "school": {"label": "School", "filename": "school.svg"},
    "academics": {"label": "Academics", "filename": "academics.svg"},
    "learning": {"label": "Learning", "filename": "learning.svg"},
    "community": {"label": "Community", "filename": "community.svg"},
    "announcement": {"label": "Announcement", "filename": "announcement.svg"},
    "fundraiser": {"label": "Fundraiser", "filename": "fundraiser.svg"},
    "service": {"label": "Service", "filename": "service.svg"},
    "supply-drive": {"label": "Supply Drive", "filename": "supply-drive.svg"},
    "clothing-drive": {"label": "Clothing Drive", "filename": "clothing-drive.svg"},
    "food-drive": {"label": "Food Drive", "filename": "food-drive.svg"},
}

ICON_GROUPS: list[dict[str, Any]] = [
    {
        "label": "Sports",
        "options": [
            {"value": "soccer", "label": "Soccer"},
            {"value": "football", "label": "Football"},
            {"value": "basketball", "label": "Basketball"},
            {"value": "baseball", "label": "Baseball"},
            {"value": "lacrosse", "label": "Lacrosse"},
            {"value": "golf", "label": "Golf"},
            {"value": "volleyball", "label": "Volleyball"},
            {"value": "hockey", "label": "Hockey"},
            {"value": "swimming", "label": "Swimming"},
            {"value": "running", "label": "Running"},
            {"value": "tennis", "label": "Tennis"},
            {"value": "competition", "label": "Competition"},
            {"value": "medal", "label": "Medal"},
            {"value": "trophy", "label": "Trophy"},
        ],
    },
    {
        "label": "Arts",
        "options": [
            {"value": "music", "label": "Music"},
            {"value": "performance", "label": "Performance"},
            {"value": "theater", "label": "Theater"},
            {"value": "visual-arts", "label": "Visual Arts"},
            {"value": "camera", "label": "Photo / Media"},
            {"value": "showcase", "label": "Showcase"},
        ],
    },
    {
        "label": "School Events",
        "options": [
            {"value": "calendar", "label": "Calendar"},
            {"value": "school", "label": "School"},
            {"value": "academics", "label": "Academics"},
            {"value": "learning", "label": "Learning"},
            {"value": "community", "label": "Community"},
            {"value": "announcement", "label": "Announcement"},
            {"value": "fundraiser", "label": "Fundraiser"},
            {"value": "service", "label": "Service"},
            {"value": "supply-drive", "label": "Supply Drive"},
            {"value": "clothing-drive", "label": "Clothing Drive"},
            {"value": "food-drive", "label": "Food Drive"},
            {"value": "camera", "label": "Student Media"},
        ],
    },
]

LEGACY_ICON_ALIASES = {
    "futbol": "soccer",
    "football": "football",
    "basketball": "basketball",
    "baseball": "baseball",
    "shield-halved": "lacrosse",
    "golf-ball-tee": "golf",
    "volleyball": "volleyball",
    "hockey-puck": "hockey",
    "person-swimming": "swimming",
    "person-running": "running",
    "flag-checkered": "competition",
    "medal": "medal",
    "trophy": "trophy",
    "music": "music",
    "microphone-lines": "performance",
    "masks-theater": "theater",
    "palette": "visual-arts",
    "camera": "camera",
    "star": "showcase",
    "calendar-days": "calendar",
    "graduation-cap": "academics",
    "book-open": "learning",
    "users": "community",
    "bullhorn": "announcement",
    "hand-holding-dollar": "fundraiser",
    "handshake-angle": "service",
    "box-open": "supply-drive",
    "shirt": "clothing-drive",
    "utensils": "food-drive",
}

ICON_LABELS = {key: value["label"] for key, value in ICON_REGISTRY.items()}


def normalize_icon_key(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    canonical = LEGACY_ICON_ALIASES.get(raw, raw)
    return canonical if canonical in ICON_REGISTRY else ""


def icon_label(icon_key: str) -> str:
    canonical = normalize_icon_key(icon_key)
    if not canonical:
        return "Auto Select"
    return ICON_LABELS.get(canonical, canonical.replace("-", " ").title())


def icon_static_path(icon_key: str) -> str:
    canonical = normalize_icon_key(icon_key)
    if not canonical:
        return ""
    filename = ICON_REGISTRY[canonical]["filename"]
    return f"{ICON_STATIC_PREFIX}/{filename}"


def icon_public_url(icon_key: str, *, base_url: str = "") -> str:
    path = icon_static_path(icon_key)
    if not path:
        return ""
    clean_base = str(base_url or "").strip().rstrip("/")
    return f"{clean_base}{path}" if clean_base else path
