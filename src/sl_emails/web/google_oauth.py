from __future__ import annotations

from typing import Any

try:
    from authlib.integrations.flask_client import OAuth
except ImportError:  # pragma: no cover
    OAuth = None  # type: ignore[assignment]


oauth = OAuth() if OAuth is not None else None


def google_oauth_enabled(app_config: dict[str, Any]) -> bool:
    return bool(
        oauth is not None
        and str(app_config.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        and str(app_config.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
    )


def init_google_oauth(app: Any) -> None:
    if oauth is None:
        return
    oauth.init_app(app)
    if not google_oauth_enabled(app.config):
        return
    oauth.register(
        name="google",
        client_id=str(app.config.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip(),
        client_secret=str(app.config.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip(),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "prompt": "select_account"},
    )


__all__ = ["google_oauth_enabled", "init_google_oauth", "oauth"]
