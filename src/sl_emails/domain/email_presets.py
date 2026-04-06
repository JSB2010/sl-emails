from __future__ import annotations

from .iconography import ICON_GROUPS, icon_label


CURATED_ICON_GROUPS = ICON_GROUPS

REQUEST_SPORT_OPTIONS = [
    {"value": "Baseball", "label": "Baseball", "icon": "baseball"},
    {"value": "Basketball", "label": "Basketball", "icon": "basketball"},
    {"value": "Cross Country", "label": "Cross Country", "icon": "running"},
    {"value": "Field Hockey", "label": "Field Hockey", "icon": "hockey"},
    {"value": "Football", "label": "Football", "icon": "football"},
    {"value": "Golf", "label": "Golf", "icon": "golf"},
    {"value": "Ice Hockey", "label": "Ice Hockey", "icon": "hockey"},
    {"value": "Lacrosse", "label": "Lacrosse", "icon": "lacrosse"},
    {"value": "Soccer", "label": "Soccer", "icon": "soccer"},
    {"value": "Swimming", "label": "Swimming", "icon": "swimming"},
    {"value": "Tennis", "label": "Tennis", "icon": "tennis"},
    {"value": "Track", "label": "Track", "icon": "running"},
    {"value": "Volleyball", "label": "Volleyball", "icon": "volleyball"},
]

REQUEST_EVENT_CATEGORY_OPTIONS = [
    {"value": "Admissions", "label": "Admissions", "icon": "school", "description": "Open houses, visit programs, and family events."},
    {"value": "Academic", "label": "Academic", "icon": "academics", "description": "Lectures, showcases, and academic milestones."},
    {"value": "Announcement", "label": "Announcement", "icon": "announcement", "description": "Important schoolwide notices or reminders."},
    {"value": "Assembly", "label": "Assembly", "icon": "school", "description": "Divisional gatherings and speaker programs."},
    {"value": "Club Meeting", "label": "Club Meeting", "icon": "community", "description": "Student club meetings, interest sessions, and sign-ups."},
    {"value": "Community", "label": "Community", "icon": "community", "description": "Community nights, celebrations, and parent-facing events."},
    {"value": "Fundraiser", "label": "Fundraiser", "icon": "fundraiser", "description": "Benefit nights, ticket sales, and fundraising campaigns."},
    {"value": "Service", "label": "Service", "icon": "service", "description": "Volunteer events and service projects."},
    {"value": "Performance", "label": "Performance", "icon": "performance", "description": "Concerts, recitals, theater, and live performances."},
    {"value": "Showcase", "label": "Showcase", "icon": "showcase", "description": "Exhibits, showcases, and featured presentations."},
    {"value": "Food Drive", "label": "Food Drive", "icon": "food-drive", "description": "Canned food and pantry item collection drives."},
    {"value": "Book Drive", "label": "Book Drive", "icon": "learning", "description": "Book donation drives and reading campaigns."},
    {"value": "Clothing Drive", "label": "Clothing Drive", "icon": "clothing-drive", "description": "Clothing, outerwear, and uniform collection drives."},
    {"value": "Supply Drive", "label": "Supply Drive", "icon": "supply-drive", "description": "School supply, toiletry, or equipment donation drives."},
    {"value": "Media", "label": "Media / Publication", "icon": "camera", "description": "Yearbook, newspaper, photography, and publication deadlines."},
]

SPORT_CONFIG = {
    "soccer": {"icon": "soccer", "border_color": "#0066ff", "accent_color": "#0066ff"},
    "football": {"icon": "football", "border_color": "#a11919", "accent_color": "#a11919"},
    "tennis": {"icon": "tennis", "border_color": "#13cf97", "accent_color": "#13cf97"},
    "golf": {"icon": "golf", "border_color": "#f2b900", "accent_color": "#f2b900"},
    "cross country": {"icon": "running", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "field hockey": {"icon": "hockey", "border_color": "#ec4899", "accent_color": "#ec4899"},
    "volleyball": {"icon": "volleyball", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "basketball": {"icon": "basketball", "border_color": "#f97316", "accent_color": "#f97316"},
    "lacrosse": {"icon": "lacrosse", "border_color": "#10b981", "accent_color": "#10b981"},
    "baseball": {"icon": "baseball", "border_color": "#3b82f6", "accent_color": "#3b82f6"},
    "swimming": {"icon": "swimming", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "track": {"icon": "running", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "ice hockey": {"icon": "hockey", "border_color": "#64748b", "accent_color": "#64748b"},
}

ARTS_CONFIG = {
    "dance": {"icon": "music", "border_color": "#ec4899", "accent_color": "#ec4899"},
    "music": {"icon": "music", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "theater": {"icon": "theater", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "theatre": {"icon": "theater", "border_color": "#f59e0b", "accent_color": "#f59e0b"},
    "visual": {"icon": "visual-arts", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "art": {"icon": "visual-arts", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
    "concert": {"icon": "music", "border_color": "#8b5cf6", "accent_color": "#8b5cf6"},
    "performance": {"icon": "performance", "border_color": "#f97316", "accent_color": "#f97316"},
    "showcase": {"icon": "showcase", "border_color": "#eab308", "accent_color": "#eab308"},
    "exhibit": {"icon": "visual-arts", "border_color": "#06b6d4", "accent_color": "#06b6d4"},
}

SCHOOL_EVENT_CONFIG = {
    "community": {"icon": "community", "border_color": "#0c3a6b", "accent_color": "#0c3a6b"},
    "service": {"icon": "service", "border_color": "#17654c", "accent_color": "#17654c"},
    "announcement": {"icon": "announcement", "border_color": "#a11919", "accent_color": "#a11919"},
    "admissions": {"icon": "school", "border_color": "#165191", "accent_color": "#165191"},
    "academic": {"icon": "academics", "border_color": "#8c6a00", "accent_color": "#8c6a00"},
    "club": {"icon": "community", "border_color": "#7c3aed", "accent_color": "#7c3aed"},
    "meeting": {"icon": "calendar", "border_color": "#64748b", "accent_color": "#64748b"},
    "assembly": {"icon": "school", "border_color": "#165191", "accent_color": "#165191"},
    "fundraiser": {"icon": "fundraiser", "border_color": "#8c6a00", "accent_color": "#8c6a00"},
    "food drive": {"icon": "food-drive", "border_color": "#a11919", "accent_color": "#a11919"},
    "book drive": {"icon": "learning", "border_color": "#165191", "accent_color": "#165191"},
    "clothing drive": {"icon": "clothing-drive", "border_color": "#17654c", "accent_color": "#17654c"},
    "supply drive": {"icon": "supply-drive", "border_color": "#64748b", "accent_color": "#64748b"},
    "drive": {"icon": "supply-drive", "border_color": "#64748b", "accent_color": "#64748b"},
    "media": {"icon": "camera", "border_color": "#0f766e", "accent_color": "#0f766e"},
}

DEFAULT_SPORT_CONFIG = {"icon": "trophy", "border_color": "#6b7280", "accent_color": "#6b7280"}
DEFAULT_ARTS_CONFIG = {"icon": "showcase", "border_color": "#a11919", "accent_color": "#a11919"}
DEFAULT_SCHOOL_EVENT_CONFIG = {"icon": "calendar", "border_color": "#6b7280", "accent_color": "#6b7280"}

__all__ = [
    "ARTS_CONFIG",
    "CURATED_ICON_GROUPS",
    "DEFAULT_ARTS_CONFIG",
    "DEFAULT_SCHOOL_EVENT_CONFIG",
    "DEFAULT_SPORT_CONFIG",
    "REQUEST_EVENT_CATEGORY_OPTIONS",
    "REQUEST_SPORT_OPTIONS",
    "SCHOOL_EVENT_CONFIG",
    "SPORT_CONFIG",
    "icon_label",
]
