import unittest
from datetime import date, datetime
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

from sl_emails.ingest import generate_games


def _response(html: str) -> Mock:
    response = Mock()
    response.content = html.encode("utf-8")
    response.text = html
    response.raise_for_status.return_value = None
    return response


def _game_row(team: str, opponent: str, date: str, *, time: str = "4:00 PM", location: str = "Main Gym", advantage: str = "Home") -> str:
    return (
        "<tr>"
        f"<td>{team}</td>"
        f"<td>vs. {opponent}</td>"
        f"<td>{date}</td>"
        f"<td>{time}</td>"
        f"<td>{location}</td>"
        f"<td>{advantage}</td>"
        "</tr>"
    )


class _FakeDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 4, 12, 0, 0)


class _FakeDtStart:
    def __init__(self, value):
        self.dt = value


class _FakeCalendar:
    def __init__(self, components):
        self._components = components

    def walk(self):
        return list(self._components)


class _FakeComponent:
    name = "VEVENT"

    def __init__(self, *, summary="Untitled Event", location="TBA", dtstart=None):
        self._data = {"summary": summary, "location": location, "dtstart": dtstart}

    def get(self, key, default=None):
        value = self._data.get(key, default)
        if isinstance(value, Exception):
            raise value
        return value


class AthleticsLoadMoreTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(Path("mar16"), ignore_errors=True)

    def test_parse_games_from_soup_accepts_load_more_fragment_without_header(self):
        soup = BeautifulSoup(
            f"<table><tbody>{_game_row('Baseball - Varsity', 'Colorado Academy', 'Mar 17 2026')}</tbody></table>",
            "html.parser",
        )

        games, latest_date = generate_games.parse_games_from_soup(soup, "2026-03-16", "2026-03-22")

        self.assertEqual(len(games), 1)
        self.assertEqual(games[0].team, "Baseball - Varsity")
        self.assertEqual(latest_date.isoformat(), "2026-03-17")

    @patch("sl_emails.ingest.generate_games.requests.get")
    def test_scrape_athletics_schedule_uses_finalsite_load_more_endpoint(self, mock_get):
        initial_html = f"""
        <html>
          <body data-pageid="1626">
            <div class="fsElement fsAthleticsEvent" id="fsEl_39786">
              <table>
                <tbody>
                  <tr><th>Team</th><th>Opponent</th><th>Date</th><th>Time</th><th>Location</th><th>Advantage</th></tr>
                  {_game_row('Baseball - Varsity', 'Colorado Academy', 'Mar 10 2026')}
                  <tr class="fsLoadMoreButtonRow"><td colspan="6"><button class="fsLoadMoreButton" data-start-row="26">Load More</button></td></tr>
                </tbody>
              </table>
            </div>
          </body>
        </html>
        """
        load_more_html = f"""
        <div class="fsElement fsAthleticsEvent" id="fsEl_39786">
          <table>
            <tbody>
              {_game_row('Girls Soccer - Varsity', 'Denver South', 'Mar 17 2026', advantage='Away')}
            </tbody>
          </table>
        </div>
        """
        mock_get.side_effect = [_response(initial_html), _response(load_more_html)]

        games = generate_games.scrape_athletics_schedule("2026-03-09", "2026-03-20")

        self.assertEqual([game.team for game in games], ["Baseball - Varsity", "Girls Soccer - Varsity"])
        self.assertEqual(mock_get.call_count, 2)
        _, first_kwargs = mock_get.call_args_list[0]
        second_args, second_kwargs = mock_get.call_args_list[1]
        self.assertEqual(first_kwargs["headers"], generate_games.build_kent_denver_headers())
        self.assertEqual(second_args[0], "https://www.kentdenver.org/fs/elements/39786")
        self.assertEqual(
            second_kwargs["params"],
            {
                "is_load_more": "true",
                "page_id": "1626",
                "parent_id": "39786",
                "start_row": "26",
            },
        )

    def test_helper_renderers_configs_and_parsers_cover_fallbacks(self):
        icon_img = generate_games.build_icon_html("calendar-days", "Calendar Icon", size=18, icon_base_url="https://example.test")
        icon_fallback = generate_games.build_icon_html("", "Basketball", size=18)
        self.assertIn("https://example.test/static/icons/calendar.svg", icon_img)
        self.assertIn(">B</span>", icon_fallback)
        self.assertEqual(generate_games.escape_html('A&B "quoted"'), "A&amp;B &quot;quoted&quot;")
        self.assertEqual(generate_games.format_copy_html("Line 1\nLine 2"), "Line 1<br />Line 2")

        full_details = generate_games.render_optional_details_html("Bring a snack", "https://example.test", accent_color="#0066ff")
        list_details = generate_games.render_optional_list_details_html("Bring a snack", "https://example.test", accent_color="#0066ff")
        self.assertIn("Bring a snack", full_details)
        self.assertIn("More details", full_details)
        self.assertIn("Bring a snack", list_details)
        self.assertEqual(generate_games.render_optional_details_html("", "", accent_color="#0066ff"), "")
        self.assertEqual(generate_games.render_optional_list_details_html("", "", accent_color="#0066ff"), "")

        game = generate_games.Game("Baseball - Varsity", "CA", "Mar 10 2026", "4:00 PM", "Main Gym", True, "baseball", icon="star")
        away_game = generate_games.Game("Unknown Team", "CA", "Mar 10 2026", "4:00 PM", "Main Gym", False, "unknown")
        event = generate_games.Event("Spring Concert", "Mar 11 2026", "7:00 PM", "PAC", "music", icon="sparkles")
        school_event = generate_games.Event("Community Gathering", "Mar 11 2026", "All Day", "Campus", "community")
        self.assertEqual(game.get_sport_config()["icon"], "star")
        self.assertEqual(away_game.get_sport_config()["icon"], generate_games.DEFAULT_SPORT_CONFIG["icon"])
        self.assertEqual(game.get_home_away_style()["text"], "Home")
        self.assertEqual(away_game.get_home_away_style()["text"], "Away")
        self.assertEqual(event.get_sport_config()["icon"], "sparkles")
        self.assertEqual(school_event.get_sport_config()["icon"], generate_games.SCHOOL_EVENT_CONFIG["community"]["icon"])
        self.assertEqual(event.get_home_away_style()["text"], "Event")

    def test_parse_and_collection_helpers_cover_edge_cases(self):
        no_table_soup = BeautifulSoup("<div>No table</div>", "html.parser")
        self.assertEqual(generate_games.parse_games_from_soup(no_table_soup, "2026-03-09", "2026-03-15"), ([], None))

        soup = BeautifulSoup(
            (
                "<table><tbody>"
                f"{_game_row('Girls Soccer - Varsity', 'Denver South', 'Mar172026', advantage='Away')}"
                f"{_game_row('Track and Field', 'League Meet', 'Apr102026-Apr112026')}"
                f"{_game_row('Broken Date Team', 'Opponent', 'NotADate')}"
                "<tr><td>Short</td></tr>"
                "</tbody></table>"
            ),
            "html.parser",
        )
        games, latest_date = generate_games.parse_games_from_soup(soup, "2026-03-16", "2026-04-12")
        self.assertEqual([game.team for game in games], ["Girls Soccer - Varsity", "Track and Field"])
        self.assertFalse(games[0].is_home)
        self.assertEqual(games[1].date, "Apr 10 2026")
        self.assertEqual(latest_date.isoformat(), "2026-04-10")

        duplicate = generate_games.Game("Girls Soccer - Varsity", "Denver South", "Mar 17 2026", "4:00 PM", "Main Gym", False, "soccer")
        unique = generate_games.Game("Baseball - Varsity", "Colorado Academy", "Mar 18 2026", "4:00 PM", "Main Gym", True, "baseball")
        combined = generate_games.extend_unique_games([duplicate], [duplicate, unique])
        self.assertEqual([game.team for game in combined], ["Girls Soccer - Varsity", "Baseball - Varsity"])

        context_html = """
        <html><body data-pageid="1626">
          <div class="fsElement fsAthleticsEvent" id="fsEl_39786">
            <table><tbody><tr><td>ok</td></tr></tbody></table>
            <button class="fsLoadMoreButton" data-start-row="26">Load More</button>
          </div>
        </body></html>
        """
        context_soup = BeautifulSoup(context_html, "html.parser")
        self.assertEqual(
            generate_games.extract_load_more_context(context_soup, context_html),
            {"page_id": "1626", "element_id": "39786", "start_row": "26"},
        )
        self.assertIsNone(generate_games.extract_load_more_context(BeautifulSoup("<table></table>", "html.parser"), "<html></html>"))

    @patch("sl_emails.ingest.generate_games.requests.get")
    def test_stage1_stage2_and_arts_fetch_cover_success_and_failure_paths(self, mock_get):
        stage1_html = f"<table><tbody>{_game_row('Baseball - Varsity', 'Colorado Academy', 'Mar 20 2026')}</tbody></table>"
        mock_get.return_value = _response(stage1_html)
        direct_games = generate_games.scrape_athletics_schedule("2026-03-16", "2026-03-20")
        self.assertEqual(len(direct_games), 1)

        with patch("sl_emails.ingest.generate_games.requests.get", side_effect=generate_games.requests.RequestException("boom")):
            with patch("sl_emails.ingest.generate_games.scrape_athletics_schedule_with_load_more", return_value=["fallback"]) as fallback:
                self.assertEqual(generate_games.scrape_athletics_schedule("2026-03-16", "2026-03-20"), ["fallback"])
                fallback.assert_called_once()

        initial_html = "<html><body><table><tbody></tbody></table></body></html>"
        mock_get.side_effect = [_response(initial_html)]
        result = generate_games.scrape_athletics_schedule_with_load_more("2026-03-16", "2026-03-20")
        self.assertEqual(result, [])

        with patch("sl_emails.ingest.generate_games.requests.get", side_effect=generate_games.requests.RequestException("load more failed")):
            with self.assertRaises(RuntimeError):
                generate_games.scrape_athletics_schedule_with_load_more("2026-03-16", "2026-03-20")

        arts_response = Mock()
        arts_response.raise_for_status.return_value = None
        arts_response.content = b"BEGIN:VCALENDAR"
        datetime_component = _FakeComponent(
            summary="Spring Concert",
            location="PAC",
            dtstart=_FakeDtStart(datetime(2026, 3, 18, 19, 0)),
        )
        date_component = _FakeComponent(
            summary="Community Advisory",
            location="Campus Center",
            dtstart=_FakeDtStart(date(2026, 3, 19)),
        )
        broken_component = _FakeComponent(summary=ValueError("bad component"))
        with (
            patch("sl_emails.ingest.generate_games.requests.get", return_value=arts_response),
            patch("sl_emails.ingest.generate_games.Calendar.from_ical", return_value=_FakeCalendar([datetime_component, date_component, broken_component])),
        ):
            arts_events = generate_games.fetch_arts_events("2026-03-16", "2026-03-20")
        self.assertEqual([event.title for event in arts_events], ["Spring Concert", "Community Advisory"])
        self.assertEqual(arts_events[0].time, "7:00 PM")
        self.assertEqual(arts_events[1].time, "All Day")

        with patch("sl_emails.ingest.generate_games.requests.get", side_effect=generate_games.requests.RequestException("ical down")):
            with self.assertRaises(RuntimeError):
                generate_games.fetch_arts_events("2026-03-16", "2026-03-20")

    def test_date_category_priority_and_card_helpers_cover_branching_logic(self):
        with patch("sl_emails.ingest.generate_games.datetime", _FakeDateTime):
            self.assertEqual(generate_games.get_current_week(), ("2026-03-02", "2026-03-08"))
            self.assertEqual(generate_games.get_next_week(), ("2026-03-09", "2026-03-15"))

        self.assertEqual(generate_games.extract_sport_from_team("XC Varsity"), "cross country")
        self.assertEqual(generate_games.extract_sport_from_team("Track and Field"), "track")
        self.assertEqual(generate_games.extract_sport_from_team("Mystery Team"), "other")
        self.assertEqual(generate_games.extract_arts_category("Spring Music Concert"), "music")
        self.assertEqual(generate_games.extract_arts_category("Unknown Showcase"), "showcase")
        self.assertTrue(generate_games.is_middle_school_game("Middle School Soccer"))
        self.assertFalse(generate_games.is_middle_school_game("Varsity Soccer"))
        self.assertTrue(generate_games.is_varsity_game("Varsity Soccer"))
        self.assertFalse(generate_games.is_varsity_game("JV Soccer"))
        self.assertFalse(generate_games.is_varsity_game("Middle School Soccer"))
        self.assertTrue(generate_games.is_varsity_game("Girls Tennis"))

        home_game = generate_games.Game("Middle School Soccer", "CA", "Mar 17 2026", "4:00 PM", "Main Gym", True, "soccer", description="Bring signs", link="https://example.test")
        away_game = generate_games.Game("JV Soccer", "CA", "Mar 18 2026", "5:00 PM", "Main Gym", False, "soccer")
        arts_event = generate_games.Event("Spring Concert", "Mar 19 2026", "7:00 PM", "PAC", "music", description="Doors at 6:30", link="https://example.test")

        self.assertTrue(generate_games.is_featured_game(home_game, True))
        self.assertFalse(generate_games.is_featured_game(away_game, True))
        self.assertTrue(generate_games.is_featured_game(arts_event, False))
        featured, other = generate_games.categorize_games_by_priority([home_game, away_game, arts_event], is_middle_school=False)
        self.assertEqual(len(featured), 2)
        self.assertEqual(len(other), 1)

        middle, upper = generate_games.separate_games_by_school([home_game, away_game, arts_event])
        self.assertEqual([event.team for event in middle], ["Middle School Soccer"])
        self.assertEqual([event.team for event in upper], ["JV Soccer", "Spring Concert"])

        missing = generate_games.get_missing_weekdays(
            {"Mar 17 2026": [home_game], "Mar 19 2026": [arts_event], "bad-date": [away_game]},
            "2026-03-16",
            "2026-03-20",
        )
        self.assertEqual(missing, ["Mar 18 2026"])
        self.assertEqual(generate_games.format_date_range("2026-03-16", "2026-03-20"), "March 16–20, 2026")
        self.assertEqual(generate_games.format_date_range("2026-03-30", "2026-04-02"), "March 30–April 02, 2026")
        self.assertEqual(generate_games.format_date_range("2025-12-29", "2026-01-02"), "December 29, 2025–January 02, 2026")

        sports_text = generate_games.get_dynamic_text_variations("2026-03-16", has_arts_events=False)
        arts_text = generate_games.get_dynamic_text_variations("2026-03-16", has_arts_events=True)
        self.assertIn("{sport_count}", sports_text["hero_text"])
        self.assertIn("perform", arts_text["hero_text"].lower())

        featured_event_html = generate_games.generate_featured_event_card_html(arts_event, icon_base_url="https://example.test")
        featured_game_html = generate_games.generate_featured_game_card_html(
            generate_games.Game("Varsity Soccer", "CA", "Mar 17 2026", "4:00 PM", "Main Gym", True, "soccer"),
            icon_base_url="https://example.test",
        )
        other_event_html = generate_games.generate_other_event_list_item_html(arts_event)
        other_game_html = generate_games.generate_other_game_list_item_html(away_game)
        self.assertIn("More details", featured_event_html)
        self.assertIn("Home", featured_game_html)
        self.assertIn("Varsity", featured_game_html)
        self.assertIn("Spring Concert", other_event_html)
        self.assertIn("Away", other_game_html)

    def test_generate_html_email_and_main_cover_render_and_cli_paths(self):
        game = generate_games.Game("Varsity Soccer", "Front Range", "Mar 17 2026", "4:00 PM", "Main Field", True, "soccer")
        event = generate_games.Event("Spring Concert", "Mar 19 2026", "7:00 PM", "PAC", "music")
        extra = generate_games.Game("JV Soccer", "Rival", "Mar 17 2026", "5:00 PM", "Aux Field", False, "soccer")
        grouped = generate_games.group_games_by_date([game, extra, event])
        html = generate_games.generate_html_email(
            grouped,
            "March 16–20, 2026",
            "Music, Soccer",
            "2026-03-16",
            "2026-03-20",
            "Upper School",
            heading="Custom Heading",
            intro_note="Bring a friend.\nDoors open early.",
            email_subject="Weekly Digest",
            copy_overrides={
                "hero_text": "A custom hero line",
                "intro_title": "Custom intro",
                "intro_text": "The week ahead.",
                "spotlight_label": "Featured",
                "schedule_label": "Lineup",
                "also_on_schedule_label": "More to know",
                "empty_day_template": "Nothing on {weekday}.",
                "cta_eyebrow": "Plan ahead",
                "cta_title": "Support students",
                "cta_text": "Show up if you can.",
            },
            icon_base_url="https://example.test",
        )
        self.assertIn("Custom Heading", html)
        self.assertIn("A custom hero line", html)
        self.assertIn("Custom intro", html)
        self.assertIn("Bring a friend.<br />Doors open early.", html)
        self.assertIn("Nothing on Wednesday.", html)
        self.assertIn("Featured", html)
        self.assertIn("More to know", html)
        self.assertIn("Support students", html)
        self.assertIn('meta name="has-arts-events" content="true"', html)
        self.assertIn("https://example.test/static/icons", html)

        with TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "emails"
            middle_school_game = generate_games.Game("Middle School Soccer", "Front Range", "Mar 18 2026", "4:00 PM", "Main Field", True, "soccer")
            with (
                patch("sl_emails.ingest.generate_games.scrape_athletics_schedule", return_value=[game, middle_school_game]),
                patch("sl_emails.ingest.generate_games.fetch_arts_events", return_value=[event]),
                patch(
                    "sl_emails.ingest.generate_games.generate_html_email",
                    side_effect=lambda *args, **kwargs: f"<html>{args[5]}</html>",
                ),
                patch("sys.argv", ["generate_games.py", "--start-date", "2026-03-16", "--end-date", "2026-03-20", "--output-dir", str(output_dir)]),
            ):
                generate_games.main()

            ms_path = output_dir / "games-week-middle-school-mar16.html"
            us_path = output_dir / "games-week-upper-school-mar16.html"
            self.assertEqual(ms_path.read_text(encoding="utf-8"), "<html>Middle School</html>")
            self.assertEqual(us_path.read_text(encoding="utf-8"), "<html>Upper School</html>")

        with patch("sys.argv", ["generate_games.py", "--skip-html"]):
            with self.assertRaises(SystemExit):
                generate_games.main()

        with patch("sys.argv", ["generate_games.py", "--start-date", "2026-03-16"]):
            with self.assertRaises(SystemExit):
                generate_games.main()

        with TemporaryDirectory() as tempdir:
            no_events_dir = Path(tempdir) / "no-events"
            with (
                patch("sl_emails.ingest.generate_games.scrape_athletics_schedule", return_value=[]),
                patch("sl_emails.ingest.generate_games.fetch_arts_events", return_value=[]),
                patch(
                    "sys.argv",
                    [
                        "generate_games.py",
                        "--start-date",
                        "2026-03-16",
                        "--end-date",
                        "2026-03-20",
                        "--output-dir",
                        str(no_events_dir),
                    ],
                ),
            ):
                with self.assertRaises(SystemExit):
                    generate_games.main()

            self.assertFalse(no_events_dir.exists())

    def test_main_does_not_leave_empty_output_folder_when_no_events_are_found(self):
        with TemporaryDirectory() as tempdir:
            target_dir = Path(tempdir) / "mar16"
            with (
                patch("sl_emails.ingest.generate_games.scrape_athletics_schedule", return_value=[]),
                patch("sl_emails.ingest.generate_games.fetch_arts_events", return_value=[]),
                patch("sys.argv", ["generate_games.py", "--start-date", "2026-03-16", "--end-date", "2026-03-20", "--output-dir", str(target_dir)]),
            ):
                with self.assertRaises(SystemExit):
                    generate_games.main()

            self.assertFalse(target_dir.exists())


if __name__ == "__main__":
    unittest.main()
