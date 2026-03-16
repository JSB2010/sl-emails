from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from sl_emails.web.google_oauth import google_oauth_enabled, oauth

from ..support import current_user, ensure_admin_settings, write_activity


blueprint = Blueprint("auth", __name__)


def _safe_next_url(raw_value: str | None) -> str:
    target = str(raw_value or "").strip()
    if not target or not target.startswith("/"):
        return "/emails"
    return target


@blueprint.get("/login")
def login() -> Any:
    user = current_user()
    next_url = _safe_next_url(request.args.get("next"))
    if user and str(user.get("email") or "").strip():
        settings = ensure_admin_settings()
        if str(user.get("email") or "").strip().lower() in settings.allowed_admin_emails:
            return redirect(next_url)
        return redirect(url_for("auth.access_denied"))

    return render_template(
        "login.html",
        next_url=next_url,
        start_url=f"{url_for('auth.google_start')}?next={next_url}",
        google_oauth_configured=google_oauth_enabled(current_app.config),
    )


@blueprint.get("/auth/google/start")
def google_start() -> Any:
    if not google_oauth_enabled(current_app.config) or oauth is None:
        return render_template(
            "login.html",
            next_url=_safe_next_url(request.args.get("next")),
            start_url=f"{url_for('auth.google_start')}?next={_safe_next_url(request.args.get('next'))}",
            google_oauth_configured=False,
            auth_error="Google sign-in is not configured for this environment yet.",
        ), 503

    next_url = _safe_next_url(request.args.get("next"))
    session["auth_next"] = next_url
    redirect_uri = str(current_app.config.get("GOOGLE_OAUTH_CALLBACK_URL") or "").strip() or url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@blueprint.get("/auth/google/callback")
def google_callback() -> Any:
    if not google_oauth_enabled(current_app.config) or oauth is None:
        return redirect(url_for("auth.login"))

    next_url = _safe_next_url(session.pop("auth_next", None))
    try:
        token = oauth.google.authorize_access_token()
    except Exception as exc:
        current_app.logger.exception("Google OAuth callback failed")
        session.clear()
        write_activity(event_type="auth.login", status="failed", actor="google-oauth", message=f"Google OAuth callback failed: {exc}")
        return redirect(url_for("auth.login"))
    userinfo = token.get("userinfo") if isinstance(token, dict) else None
    email = str((userinfo or {}).get("email") or "").strip().lower()
    name = str((userinfo or {}).get("name") or "").strip()
    picture = str((userinfo or {}).get("picture") or "").strip()

    if not email:
        session.clear()
        current_app.logger.error("Google callback completed without an email address")
        write_activity(event_type="auth.login", status="failed", actor="google-oauth", message="Google callback did not provide an email address")
        return redirect(url_for("auth.login"))

    settings = ensure_admin_settings()
    session["auth_user"] = {"email": email, "name": name, "picture": picture}
    if email not in settings.allowed_admin_emails:
        current_app.logger.warning("Google sign-in denied for non-allowlisted email: %s", email)
        write_activity(event_type="auth.login", status="denied", actor=email, message="Signed in successfully but is not on the allowlist")
        return redirect(url_for("auth.access_denied"))

    current_app.logger.info("Google sign-in completed for %s", email)
    write_activity(event_type="auth.login", status="success", actor=email, message="Google sign-in completed")
    return redirect(next_url)


@blueprint.get("/logout")
def logout() -> Any:
    actor = str((current_user() or {}).get("email") or "anonymous")
    session.clear()
    write_activity(event_type="auth.logout", status="success", actor=actor, message="Session cleared")
    return redirect(url_for("auth.login"))


@blueprint.get("/access-denied")
def access_denied() -> Any:
    return render_template("access_denied.html"), 403
