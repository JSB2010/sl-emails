from __future__ import annotations

SOURCE_ACCENTS = {
    "athletics": "#0C3A6B",
    "arts": "#A11919",
    "custom": "#8C6A00",
}

SPORT_ACCENT_COLORS = {
    "soccer": "#0066ff",
    "football": "#a11919",
    "tennis": "#13cf97",
    "golf": "#f2b900",
    "cross country": "#8b5cf6",
    "field hockey": "#ec4899",
    "volleyball": "#f59e0b",
    "basketball": "#f97316",
    "lacrosse": "#10b981",
    "baseball": "#3b82f6",
    "swimming": "#06b6d4",
    "track": "#8b5cf6",
    "ice hockey": "#64748b",
}

ARTS_ACCENT_COLORS = {
    "dance": "#ec4899",
    "music": "#8b5cf6",
    "theater": "#f59e0b",
    "theatre": "#f59e0b",
    "visual": "#06b6d4",
    "art": "#06b6d4",
    "concert": "#8b5cf6",
    "performance": "#f97316",
    "showcase": "#eab308",
    "exhibit": "#06b6d4",
}

_SOURCE_ORDER = {"athletics": 0, "arts": 1, "custom": 2}


def source_order(source: str) -> int:
    return _SOURCE_ORDER.get(source, 3)


def accent_from_sport(sport: str, source: str) -> str:
    sport_lower = (sport or "").lower()
    for key, color in SPORT_ACCENT_COLORS.items():
        if key in sport_lower:
            return color.upper()
    return SOURCE_ACCENTS.get(source, SOURCE_ACCENTS["athletics"])
