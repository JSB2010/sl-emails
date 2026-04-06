from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

import requests

from sl_emails.domain.weekly import WeeklyDraftRecord, default_copy_overrides


GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
COPY_SYSTEM_INSTRUCTION = (
    "You write weekly Kent Denver email copy for families and students. "
    "Your job is to turn the provided schedule context into concise, useful, school-appropriate editorial copy. "
    "This is a school-wide bulletin assembled by student leadership, so the tone should feel organized, informed, welcoming, and grounded. "
    "It should not sound like marketing copy, admissions copy, or social media hype. "
    "Be specific to the week's events, but never invent details that are not in the input. "
    "Prefer clear, grounded language over hype. Avoid cliches, marketing language, emojis, and unnecessary exclamation points. "
    "If the week does not justify a special line, leave that field empty instead of forcing copy.\n\n"
    "Output requirements:\n"
    "- Return JSON only with no markdown fences or explanation.\n"
    "- Match the requested JSON shape exactly.\n"
    "- Keep subject lines under 90 characters.\n"
    "- Keep copy parent-friendly, upbeat, and informative.\n"
    "- Favor neutral, bulletin-style phrasing over promotional phrasing.\n"
    "- Avoid sounding salesy or overly invitational; support language should stay modest.\n"
    "- Do not mention scores, results, or claims that are not in the source context.\n"
    "- `empty_day_template` must include the literal token {weekday}.\n"
    "- `notes` may be empty if no extra intro note is needed.\n"
    "- `spotlight_label`, `schedule_label`, and `also_on_schedule_label` should stay short.\n"
    "- `cta_text` should sound like a short invitation to show up and support students.\n"
)


class GeminiCopyError(RuntimeError):
    pass


def _visible_events(week: WeeklyDraftRecord) -> list[Any]:
    return [event for event in week.events if str(event.status or "active").strip().lower() not in {"hidden", "inactive", "archived"}]


def _audience_summary(week: WeeklyDraftRecord, audience: str) -> dict[str, Any]:
    visible = [event for event in _visible_events(week) if audience in event.audiences]
    sports = [event.category for event in visible if event.kind == "game"]
    noteworthy_terms: list[str] = []
    for event in visible:
        haystack = " ".join([event.title, event.subtitle, event.category, event.description]).lower()
        for term in ("tournament", "playoff", "playoffs", "championship", "final", "semifinal"):
            if term in haystack and term not in noteworthy_terms:
                noteworthy_terms.append(term)
    return {
        "event_count": len(visible),
        "sports": Counter(sports).most_common(6),
        "home_events": sum(1 for event in visible if getattr(event, "is_home", False)),
        "away_events": sum(1 for event in visible if event.kind == "game" and not getattr(event, "is_home", False)),
        "has_arts": any(event.kind != "game" or event.source == "arts" for event in visible),
        "noteworthy_terms": noteworthy_terms,
    }


def _week_context_text(week: WeeklyDraftRecord) -> str:
    visible = _visible_events(week)
    lines = [
        f"Week: {week.start_date} to {week.end_date}",
        f"Heading: {week.heading or 'n/a'}",
        f"Admin note: {week.notes or 'n/a'}",
        f"Visible events: {len(visible)}",
    ]
    for audience in ("middle-school", "upper-school"):
        summary = _audience_summary(week, audience)
        sports_list = ", ".join(f"{label} ({count})" for label, count in summary["sports"]) or "none"
        terms = ", ".join(summary["noteworthy_terms"]) or "none"
        lines.extend(
            [
                f"Audience {audience}:",
                f"  event_count={summary['event_count']}",
                f"  sports={sports_list}",
                f"  home_events={summary['home_events']}",
                f"  away_events={summary['away_events']}",
                f"  has_arts={summary['has_arts']}",
                f"  noteworthy_terms={terms}",
            ]
        )
    lines.append("Events:")
    for event in visible[:30]:
        lines.append(
            f"- [{','.join(event.audiences)}] {event.start_date} {event.time_text} | {event.title} | "
            f"{event.subtitle or event.category} | {event.location} | source={event.source}"
        )
    return "\n".join(lines)


def _build_generation_prompt(week: WeeklyDraftRecord) -> str:
    return (
        "Return JSON matching this exact shape: "
        '{"heading":"","notes":"","subject_overrides":{"middle-school":"","upper-school":""},'
        '"copy_overrides":{"hero_text":"","intro_title":"","intro_text":"","spotlight_label":"",'
        '"schedule_label":"","also_on_schedule_label":"","empty_day_template":"","cta_eyebrow":"",'
        '"cta_title":"","cta_text":""}}.\n\n'
        "Field guidance:\n"
        "- `heading`: optional stronger weekly heading; use the school context, not generic sports hype.\n"
        "- `hero_text`: one short scene-setting line that reflects the week's biggest themes.\n"
        "- `intro_title`: prefer calm utility titles such as 'This week at a glance' unless the week truly warrants something more specific.\n"
        "- `intro_text`: orient the reader to what stands out this week in a factual, readable way.\n"
        "- `subject_overrides`: tailor only when the audience mix suggests a stronger line than the default; otherwise leave empty.\n"
        "- `cta_eyebrow`, `cta_title`, `cta_text`: short closing support prompt, but keep it subtle rather than promotional.\n\n"
        "Week context:\n"
        f"{_week_context_text(week)}"
    )


def _extract_json_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiCopyError("Gemini returned no candidates")
    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
    if not isinstance(parts, list):
        raise GeminiCopyError("Gemini returned an unexpected response shape")
    text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
    if not text:
        raise GeminiCopyError("Gemini returned an empty response")
    return re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()


def _normalize_generated_copy(raw: dict[str, Any]) -> dict[str, Any]:
    copy_overrides = dict(default_copy_overrides())
    raw_copy = raw.get("copy_overrides") if isinstance(raw.get("copy_overrides"), dict) else {}
    for key in copy_overrides:
        copy_overrides[key] = str(raw_copy.get(key) or "").strip()
    if copy_overrides["empty_day_template"] and "{weekday}" not in copy_overrides["empty_day_template"]:
        copy_overrides["empty_day_template"] = ""

    subjects = raw.get("subject_overrides") if isinstance(raw.get("subject_overrides"), dict) else {}
    subject_overrides = {
        audience: str(subjects.get(audience) or "").strip()[:90]
        for audience in ("middle-school", "upper-school")
        if str(subjects.get(audience) or "").strip()
    }

    return {
        "heading": str(raw.get("heading") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
        "subject_overrides": subject_overrides,
        "copy_overrides": copy_overrides,
    }


def generate_week_copy(
    week: WeeklyDraftRecord,
    *,
    api_key: str,
    model: str,
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    if not api_key:
        raise GeminiCopyError("Gemini API key is not configured")

    prompt = _build_generation_prompt(week)

    response = requests.post(
        GEMINI_API_URL_TEMPLATE.format(model=model),
        params={"key": api_key},
        json={
            "system_instruction": {"parts": [{"text": COPY_SYSTEM_INSTRUCTION}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "responseMimeType": "application/json",
            },
        },
        timeout=timeout_seconds,
    )
    if response.status_code >= 400:
        raise GeminiCopyError(f"Gemini request failed ({response.status_code}): {response.text[:240]}")

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - network/third-party edge
        raise GeminiCopyError("Gemini returned a non-JSON response") from exc

    try:
        parsed = json.loads(_extract_json_text(payload))
    except json.JSONDecodeError as exc:
        raise GeminiCopyError("Gemini returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise GeminiCopyError("Gemini returned an invalid copy payload")
    return _normalize_generated_copy(parsed)
