"""Routes for the weekly email admin UI."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, render_template

from sl_emails.poster.carousel import get_week_bounds


blueprint = Blueprint("emails_ui", __name__)


@blueprint.get("/emails")
def emails_index():
    today = datetime.now().date()
    start, end = get_week_bounds(mode="next", today=today)

    return render_template(
        "emails.html",
        default_week_id=start.isoformat(),
        default_end=end.isoformat(),
    )