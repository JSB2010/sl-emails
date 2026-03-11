import unittest
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


class AthleticsLoadMoreTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()