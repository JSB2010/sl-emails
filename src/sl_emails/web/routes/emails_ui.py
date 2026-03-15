"""Routes for the weekly email admin UI."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, render_template, request

from sl_emails.domain.dates import iso_to_date, week_end_for
from sl_emails.poster.carousel import get_week_bounds


blueprint = Blueprint("emails_ui", __name__)


@blueprint.get("/emails")
def emails_index():
    today = datetime.now().date()
    requested_week = str(request.args.get("week") or "").strip()

    if requested_week:
        try:
            start = iso_to_date(requested_week)
            end = iso_to_date(week_end_for(requested_week))
        except ValueError:
            start, end = get_week_bounds(mode="next", today=today)
    else:
        start, end = get_week_bounds(mode="next", today=today)

    return render_template(
        "emails.html",
        default_week_id=start.isoformat(),
        default_end=end.isoformat(),
    )
