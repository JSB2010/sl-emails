import unittest
from datetime import date

from sl_emails.services.event_shapes import (
    PosterEvent,
    SourceFetchStatus,
    WeekEventsFetchResult,
    audiences_for_bucket,
    fetch_week_events,
    merge_poster_events,
    poster_event_from_dict,
    poster_event_to_weekly_event_payload,
    priority_from_source_event,
    source_event_to_poster_event,
    source_event_to_weekly_event_payload,
)


class _FakeGame:
    event_type = "game"

    def __init__(self, team="Varsity Soccer", is_home=True, sport="soccer"):
        self.team = team
        self.opponent = "Front Range"
        self.date = "Mar 10 2026"
        self.time = "4:00 PM"
        self.location = "Main Field"
        self.is_home = is_home
        self.sport = sport

    def get_sport_config(self):
        return {"accent_color": "#0066ff", "border_color": "#004488"}


class _FakeArtsEvent:
    event_type = "arts"

    def __init__(self):
        self.title = "Spring Concert"
        self.category = "music"
        self.date = "Mar 11 2026"
        self.time = "7:00 PM"
        self.location = "PAC"
        self.team = "Spring Concert"

    def get_sport_config(self):
        return {"accent_color": "#A11919", "border_color": "#7A1010"}


class EventShapesTests(unittest.TestCase):
    def test_basic_shape_helpers(self):
        poster = poster_event_from_dict({"title": "", "priority": 7, "accent": "", "metadata": []})
        self.assertEqual(poster.title, "Untitled Event")
        self.assertEqual(poster.priority, 5)
        self.assertEqual(audiences_for_bucket("middle_school"), ["middle-school"])
        self.assertEqual(audiences_for_bucket("upper_school"), ["upper-school"])

    def test_priority_and_source_event_transforms(self):
        varsity_home = _FakeGame(team="Varsity Soccer", is_home=True)
        away_non_varsity = _FakeGame(team="JV Soccer", is_home=False)

        self.assertEqual(priority_from_source_event(variety_home := varsity_home, lambda team: "varsity" in team.lower()), 4)
        self.assertEqual(priority_from_source_event(away_non_varsity, lambda team: "varsity" in team.lower()), 2)
        self.assertEqual(priority_from_source_event(_FakeArtsEvent(), lambda _team: False), 4)

        weekly_game = source_event_to_weekly_event_payload(
            varsity_home,
            school_bucket="upper_school",
            is_varsity_game=lambda team: "varsity" in team.lower(),
            timestamp="2026-03-01T00:00:00Z",
        )
        weekly_arts = source_event_to_weekly_event_payload(
            _FakeArtsEvent(),
            school_bucket="upper_school",
            is_varsity_game=lambda team: "varsity" in team.lower(),
            timestamp="2026-03-01T00:00:00Z",
        )

        self.assertEqual(weekly_game["kind"], "game")
        self.assertEqual(weekly_game["badge"], "HOME")
        self.assertEqual(weekly_arts["kind"], "event")
        self.assertEqual(weekly_arts["source"], "arts")

    def test_poster_event_transforms_and_merging(self):
        athletics = source_event_to_poster_event(_FakeGame(team="JV Soccer", is_home=False), lambda team: "varsity" in team.lower())
        arts = source_event_to_poster_event(_FakeArtsEvent(), lambda team: "varsity" in team.lower())
        payload = poster_event_to_weekly_event_payload(
            PosterEvent(
                title="Robotics Night",
                subtitle="Community",
                date="2026-03-12",
                time="6:00 PM",
                location="Innovation Lab",
                category="STEM",
                source="custom",
                badge="SPECIAL",
                priority=3,
                accent="#123456",
                audiences=[],
                team="Robotics Night",
                metadata={},
            ),
            timestamp="2026-03-01T00:00:00Z",
        )

        self.assertEqual(athletics.badge, "AWAY")
        self.assertEqual(arts.source, "arts")
        self.assertEqual(payload["kind"], "event")
        self.assertEqual(payload["audiences"], ["middle-school", "upper-school"])

        merged = merge_poster_events(
            [athletics],
            [
                {
                    "title": "Community Night",
                    "date": "2026-03-09",
                    "time": "5:00 PM",
                    "location": "Campus Center",
                    "category": "Community",
                }
            ],
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].date, "2026-03-09")

    def test_fetch_week_events_collects_failures_and_sorts_successes(self):
        def athletics_fetcher(_start, _end):
            return [_FakeGame(team="JV Soccer", is_home=False), _FakeGame(team="Varsity Soccer", is_home=True)]

        def arts_fetcher(_start, _end):
            raise RuntimeError("arts unavailable")

        result = fetch_week_events(
            date(2026, 3, 9),
            date(2026, 3, 15),
            scrape_athletics_schedule=athletics_fetcher,
            fetch_arts_events=arts_fetcher,
            is_varsity_game=lambda team: "varsity" in team.lower(),
        )

        self.assertFalse(result.ok)
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.source_statuses[0].source, "athletics")
        self.assertEqual(result.source_statuses[1].source, "arts")
        self.assertFalse(result.source_statuses[1].ok)
        self.assertEqual(result.events[0].team, "Varsity Soccer")


if __name__ == "__main__":
    unittest.main()
