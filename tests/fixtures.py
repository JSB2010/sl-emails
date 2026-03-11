from __future__ import annotations


class FakeGame:
    event_type = "game"

    def __init__(self):
        self.team = "Middle School Volleyball"
        self.opponent = "Front Range"
        self.date = "Mar 10 2026"
        self.time = "4:00 PM"
        self.location = "Kent Denver Gym"
        self.is_home = True
        self.sport = "volleyball"

    def get_sport_config(self):
        return {"accent_color": "#0066ff", "border_color": "#0066ff"}


class FakeArtsEvent:
    event_type = "arts"

    def __init__(self):
        self.title = "Spring Concert"
        self.team = "Spring Concert"
        self.date = "Mar 11 2026"
        self.time = "7:00 PM"
        self.location = "Performing Arts Center"
        self.category = "music"

    def get_sport_config(self):
        return {"border_color": "#a11919"}


__all__ = ["FakeArtsEvent", "FakeGame"]