"""Routes for the weekly email admin UI."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, render_template, request

from sl_emails.domain.dates import iso_to_date, week_end_for
from sl_emails.domain.email_presets import CURATED_ICON_GROUPS
from sl_emails.poster.carousel import get_week_bounds

from ..support import auth_urls, current_user, require_emails_admin


blueprint = Blueprint("emails_ui", __name__)


@blueprint.get("/emails")
@require_emails_admin
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

    user = current_user() or {}

    return render_template(
        "emails.html",
        default_week_id=start.isoformat(),
        default_end=end.isoformat(),
        current_user_email=str(user.get("email") or ""),
        current_user_name=str(user.get("name") or ""),
        icon_options=CURATED_ICON_GROUPS,
        auth=auth_urls(),
    )
