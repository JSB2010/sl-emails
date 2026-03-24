from __future__ import annotations

from typing import Any


CURATED_ICON_GROUPS: list[dict[str, Any]] = [
    {
        "label": "Sports",
        "options": [
            {"value": "futbol", "label": "Soccer Ball"},
            {"value": "football", "label": "Football"},
            {"value": "basketball", "label": "Basketball"},
            {"value": "baseball", "label": "Baseball"},
            {"value": "shield-halved", "label": "Lacrosse"},
            {"value": "golf-ball-tee", "label": "Golf"},
            {"value": "volleyball", "label": "Volleyball"},
            {"value": "hockey-puck", "label": "Hockey"},
            {"value": "person-swimming", "label": "Swimming"},
            {"value": "person-running", "label": "Running"},
            {"value": "flag-checkered", "label": "Competition"},
            {"value": "medal", "label": "Medal"},
            {"value": "trophy", "label": "Trophy"},
        ],
    },
    {
        "label": "Arts",
        "options": [
            {"value": "music", "label": "Music"},
            {"value": "microphone-lines", "label": "Performance"},
            {"value": "masks-theater", "label": "Theater"},
            {"value": "palette", "label": "Visual Arts"},
            {"value": "camera", "label": "Photo / Media"},
            {"value": "star", "label": "Showcase"},
        ],
    },
    {
        "label": "School Events",
        "options": [
            {"value": "calendar-days", "label": "Calendar"},
            {"value": "school", "label": "School"},
            {"value": "graduation-cap", "label": "Academics"},
            {"value": "book-open", "label": "Learning"},
            {"value": "users", "label": "Community"},
            {"value": "bullhorn", "label": "Announcement"},
            {"value": "hand-holding-dollar", "label": "Fundraiser"},
            {"value": "handshake-angle", "label": "Service"},
            {"value": "box-open", "label": "Supply Drive"},
            {"value": "shirt", "label": "Clothing Drive"},
            {"value": "utensils", "label": "Food Drive"},
            {"value": "camera", "label": "Student Media"},
        ],
    },
]

REQUEST_SPORT_OPTIONS: list[dict[str, str]] = [
    {"value": "Baseball", "label": "Baseball", "icon": "baseball"},
    {"value": "Basketball", "label": "Basketball", "icon": "basketball"},
    {"value": "Cross Country", "label": "Cross Country", "icon": "person-running"},
    {"value": "Field Hockey", "label": "Field Hockey", "icon": "hockey-puck"},
    {"value": "Football", "label": "Football", "icon": "football"},
    {"value": "Golf", "label": "Golf", "icon": "golf-ball-tee"},
    {"value": "Ice Hockey", "label": "Ice Hockey", "icon": "hockey-puck"},
    {"value": "Lacrosse", "label": "Lacrosse", "icon": "shield-halved"},
    {"value": "Soccer", "label": "Soccer", "icon": "futbol"},
    {"value": "Swimming", "label": "Swimming", "icon": "person-swimming"},
    {"value": "Tennis", "label": "Tennis", "icon": "medal"},
    {"value": "Track", "label": "Track", "icon": "person-running"},
    {"value": "Volleyball", "label": "Volleyball", "icon": "volleyball"},
]

REQUEST_EVENT_CATEGORY_OPTIONS: list[dict[str, str]] = [
    {"value": "Admissions", "label": "Admissions", "icon": "school", "description": "Open houses, visit programs, and family events."},
    {"value": "Academic", "label": "Academic", "icon": "graduation-cap", "description": "Lectures, showcases, and academic milestones."},
    {"value": "Announcement", "label": "Announcement", "icon": "bullhorn", "description": "Important schoolwide notices or reminders."},
    {"value": "Assembly", "label": "Assembly", "icon": "school", "description": "Divisional gatherings and speaker programs."},
    {"value": "Club Meeting", "label": "Club Meeting", "icon": "users", "description": "Student club meetings, interest sessions, and sign-ups."},
    {"value": "Community", "label": "Community", "icon": "users", "description": "Community nights, celebrations, and parent-facing events."},
    {"value": "Fundraiser", "label": "Fundraiser", "icon": "hand-holding-dollar", "description": "Benefit nights, ticket sales, and fundraising campaigns."},
    {"value": "Service", "label": "Service", "icon": "handshake-angle", "description": "Volunteer events and service projects."},
    {"value": "Performance", "label": "Performance", "icon": "microphone-lines", "description": "Concerts, recitals, theater, and live performances."},
    {"value": "Showcase", "label": "Showcase", "icon": "star", "description": "Exhibits, showcases, and featured presentations."},
    {"value": "Food Drive", "label": "Food Drive", "icon": "utensils", "description": "Canned food and pantry item collection drives."},
    {"value": "Book Drive", "label": "Book Drive", "icon": "book-open", "description": "Book donation drives and reading campaigns."},
    {"value": "Clothing Drive", "label": "Clothing Drive", "icon": "shirt", "description": "Clothing, outerwear, and uniform collection drives."},
    {"value": "Supply Drive", "label": "Supply Drive", "icon": "box-open", "description": "School supply, toiletry, or equipment donation drives."},
    {"value": "Media", "label": "Media / Publication", "icon": "camera", "description": "Yearbook, newspaper, photography, and publication deadlines."},
]

ICON_LABELS = {
    option["value"]: option["label"]
    for group in CURATED_ICON_GROUPS
    for option in group["options"]
}

SPORT_CONFIG = {
    "soccer": {"icon": "futbol", "border_color": "#0066ff", "accent_color": "#0066ff"},
    "football": {"icon": "football", "border_color": "#a11919", "accent_color": "#a11919"},
    "tennis": {"icon": "medal", "border_color": "#13cf97", "accent_color": "#13cf97"},
    "golf": {"icon": "golf-ball-tee", "border_color": "#f2b900", "accent_color": "#f2b900"},
    "cross country": {"icon": "person-running", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "field hockey": {"icon": "hockey-puck", "border_color": "#ec4899", "accent_color": "#ec4899"},
    "volleyball": {"icon": "volleyball", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "basketball": {"icon": "basketball", "border_color": "#f97316", "accent_color": "#f97316"},
    "lacrosse": {"icon": "shield-halved", "border_color": "#10b981", "accent_color": "#10b981"},
    "baseball": {"icon": "baseball", "border_color": "#3b82f6", "accent_color": "#3b82f6"},
    "swimming": {"icon": "person-swimming", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "track": {"icon": "person-running", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "ice hockey": {"icon": "hockey-puck", "border_color": "#64748b", "accent_color": "#64748b"},
}

ARTS_CONFIG = {
    "dance": {"icon": "music", "border_color": "#ec4899", "accent_color": "#ec4899"},
    "music": {"icon": "music", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "theater": {"icon": "masks-theater", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "theatre": {"icon": "masks-theater", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "visual": {"icon": "palette", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "art": {"icon": "palette", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "concert": {"icon": "music", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "performance": {"icon": "microphone-lines", "border_color": "#f97316", "accent_color": "#f97316"},
    "showcase": {"icon": "star", "border_color": "#eab308", "accent_color": "#eab308"},
    "exhibit": {"icon": "palette", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
}

SCHOOL_EVENT_CONFIG = {
    "community": {"icon": "users", "border_color": "#0c3a6b", "accent_color": "#0c3a6b"},
    "service": {"icon": "handshake-angle", "border_color": "#17654c", "accent_color": "#17654c"},
    "announcement": {"icon": "bullhorn", "border_color": "#a11919", "accent_color": "#a11919"},
    "admissions": {"icon": "school", "border_color": "#165191", "accent_color": "#165191"},
    "academic": {"icon": "graduation-cap", "border_color": "#8c6a00", "accent_color": "#8c6a00"},
    "club": {"icon": "users", "border_color": "#7c3aed", "accent_color": "#7c3aed"},
    "meeting": {"icon": "calendar-days", "border_color": "#64748b", "accent_color": "#64748b"},
    "assembly": {"icon": "school", "border_color": "#165191", "accent_color": "#165191"},
    "fundraiser": {"icon": "hand-holding-dollar", "border_color": "#8c6a00", "accent_color": "#8c6a00"},
    "food drive": {"icon": "utensils", "border_color": "#a11919", "accent_color": "#a11919"},
    "book drive": {"icon": "book-open", "border_color": "#165191", "accent_color": "#165191"},
    "clothing drive": {"icon": "shirt", "border_color": "#17654c", "accent_color": "#17654c"},
    "supply drive": {"icon": "box-open", "border_color": "#64748b", "accent_color": "#64748b"},
    "drive": {"icon": "box-open", "border_color": "#64748b", "accent_color": "#64748b"},
    "media": {"icon": "camera", "border_color": "#0f766e", "accent_color": "#0f766e"},
}

DEFAULT_SPORT_CONFIG = {"icon": "trophy", "border_color": "#6b7280", "accent_color": "#6b7280"}
DEFAULT_ARTS_CONFIG = {"icon": "star", "border_color": "#a11919", "accent_color": "#a11919"}
DEFAULT_SCHOOL_EVENT_CONFIG = {"icon": "calendar-days", "border_color": "#6b7280", "accent_color": "#6b7280"}


def icon_label(icon_name: str) -> str:
    value = str(icon_name or "").strip()
    if not value:
        return "Auto"
    return ICON_LABELS.get(value, value.replace("-", " ").title())
