from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sl_emails.domain.weekly import WeeklyDraftRecord, WeeklyEventRecord
from sl_emails.services.gemini_copy import _normalize_generated_copy, generate_week_copy


def sample_week() -> WeeklyDraftRecord:
    return WeeklyDraftRecord(
        week_id="2026-03-09",
        start_date="2026-03-09",
        end_date="2026-03-15",
        heading="This Week at Kent Denver",
        notes="Big week for spring sports.",
        events=[
            WeeklyEventRecord(
                id="1",
                title="Varsity Girls Soccer",
                subtitle="vs. St. Mary's",
                start_date="2026-03-10",
                end_date="2026-03-10",
                time_text="4:00 PM",
                location="Home Field",
                category="Soccer",
                source="athletics",
                audiences=["upper-school"],
                kind="game",
                is_home=True,
            ),
            WeeklyEventRecord(
                id="2",
                title="Spring Play",
                subtitle="Opening night",
                start_date="2026-03-12",
                end_date="2026-03-12",
                time_text="7:00 PM",
                location="Theater",
                category="Performance",
                source="arts",
                audiences=["middle-school", "upper-school"],
                kind="event",
            ),
        ],
    )


class NormalizeGeneratedCopyTests(unittest.TestCase):
    def test_normalize_generated_copy_enforces_subject_limit_and_weekday_token(self) -> None:
        payload = _normalize_generated_copy(
            {
                "heading": "Heading",
                "notes": "Notes",
                "subject_overrides": {
                    "middle-school": "M" * 110,
                    "upper-school": "Upper subject",
                },
                "copy_overrides": {
                    "hero_text": "Hero",
                    "empty_day_template": "No events today.",
                },
            }
        )

        self.assertEqual(len(payload["subject_overrides"]["middle-school"]), 90)
        self.assertEqual(payload["subject_overrides"]["upper-school"], "Upper subject")
        self.assertEqual(payload["copy_overrides"]["hero_text"], "Hero")
        self.assertEqual(payload["copy_overrides"]["empty_day_template"], "")


class GenerateWeekCopyTests(unittest.TestCase):
    @patch("sl_emails.services.gemini_copy.requests.post")
    def test_generate_week_copy_uses_system_instruction_and_json_mode(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"heading":"Week Ahead","notes":"","subject_overrides":{"middle-school":"MS Subject","upper-school":"US Subject"},'
                                    '"copy_overrides":{"hero_text":"Hero line","intro_title":"At a glance","intro_text":"Summary text",'
                                    '"spotlight_label":"Spotlight","schedule_label":"Schedule","also_on_schedule_label":"Also on the schedule",'
                                    '"empty_day_template":"Nothing on {weekday}.","cta_eyebrow":"Support","cta_title":"Show up","cta_text":"Be there."}}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = generate_week_copy(sample_week(), api_key="test-key", model="gemini-3-flash-preview")

        self.assertEqual(result["heading"], "Week Ahead")
        _, kwargs = mock_post.call_args
        self.assertIn("system_instruction", kwargs["json"])
        self.assertEqual(kwargs["json"]["contents"][0]["role"], "user")
        self.assertEqual(kwargs["json"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(kwargs["json"]["generationConfig"]["temperature"], 0.35)
        self.assertIn("Kent Denver", kwargs["json"]["system_instruction"]["parts"][0]["text"])
        self.assertIn("Week context:", kwargs["json"]["contents"][0]["parts"][0]["text"])
        self.assertIn("Varsity Girls Soccer", kwargs["json"]["contents"][0]["parts"][0]["text"])


if __name__ == "__main__":
    unittest.main()
