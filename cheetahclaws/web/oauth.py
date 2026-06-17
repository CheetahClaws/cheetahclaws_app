"""Third-party (OAuth2) sign-in for the web chat UI — Google, GitHub, WeChat.

Authorization-code flow. Credentials come from env vars, so a provider's button
only appears once it's configured:

  GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET
  GITHUB_OAUTH_CLIENT_ID / GITHUB_OAUTH_CLIENT_SECRET
  WECHAT_OAUTH_APP_ID    / WECHAT_OAUTH_APP_SECRET

Register the app with each provider and set the callback / redirect URI to:
  <your-origin>/api/auth/oauth/<provider>/callback

This module only builds URLs and talks to the providers; the server wires the
two endpoints and the find-or-create-user + JWT issuance.
"""
from __future__ import annotations

import os
import secrets
from typing import Optional
from urllib.parse import urlencode

# Per-provider wiring. ``id_param`` / ``secret_param`` differ because WeChat
# uses appid/secret instead of client_id/client_secret.
PROVIDERS: dict[str, dict] = {
    "google": {
        "label": "Google",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "id_env": "GOOGLE_OAUTH_CLIENT_ID",
        "secret_env": "GOOGLE_OAUTH_CLIENT_SECRET",
        "id_param": "client_id", "secret_param": "client_secret",
    },
    "github": {
        "label": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "id_env": "GITHUB_OAUTH_CLIENT_ID",
        "secret_env": "GITHUB_OAUTH_CLIENT_SECRET",
        "id_param": "client_id", "secret_param": "client_secret",
    },
    "wechat": {
        "label": "WeChat",
        # qrconnect renders the scan page; the URL needs a #wechat_redirect tail.
        "authorize_url": "https://open.weixin.qq.com/connect/qrconnect",
        "token_url": "https://api.weixin.qq.com/sns/oauth2/access_token",
        "userinfo_url": "https://api.weixin.qq.com/sns/userinfo",
        "scope": "snsapi_login",
        "id_env": "WECHAT_OAUTH_APP_ID",
        "secret_env": "WECHAT_OAUTH_APP_SECRET",
        "id_param": "appid", "secret_param": "secret",
    },
}

_HTTP_TIMEOUT = 15.0


def provider_config(name: str) -> Optional[dict]:
    """Return the provider config with credentials resolved, or None if the
    provider is unknown or not configured (missing client id/secret)."""
    p = PROVIDERS.get(name)
    if not p:
        return None
    client_id = os.environ.get(p["id_env"], "").strip()
    client_secret = os.environ.get(p["secret_env"], "").strip()
    if not client_id or not client_secret:
        return None
    return {**p, "name": name, "client_id": client_id, "client_secret": client_secret}


def configured_providers() -> list[dict]:
    """[{name, label}] for every provider that has credentials set."""
    out = []
    for name, p in PROVIDERS.items():
        if provider_config(name):
            out.append({"name": name, "label": p["label"]})
    return out


def new_state() -> str:
    return secrets.token_urlsafe(24)


def build_authorize_url(cfg: dict, redirect_uri: str, state: str) -> str:
    params = {
        cfg["id_param"]: cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    url = f"{cfg['authorize_url']}?{urlencode(params)}"
    if cfg["name"] == "wechat":
        # WeChat requires this exact fragment, and prefers appid first.
        url += "#wechat_redirect"
    return url


def exchange_and_fetch(cfg: dict, code: str, redirect_uri: str) -> Optional[dict]:
    """Exchange the auth code and fetch the user → {provider, sub, email, name}.
    Returns None on any failure. Never raises (so the server can show a clean
    error). Secrets are never logged here."""
    try:
        import httpx
    except Exception:
        return None
    name = cfg["name"]
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as cx:
            if name == "wechat":
                return _wechat(cx, cfg, code)
            return _oauth2(cx, cfg, code, redirect_uri)
    except Exception:
        return None


def _oauth2(cx, cfg, code, redirect_uri) -> Optional[dict]:
    """Standard OAuth2 (Google, GitHub)."""
    data = {
        cfg["id_param"]: cfg["client_id"],
        cfg["secret_param"]: cfg["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    tok = cx.post(cfg["token_url"], data=data,
                  headers={"Accept": "application/json"})
    access = (tok.json() or {}).get("access_token")
    if not access:
        return None

    if cfg["name"] == "github":
        u = cx.get(cfg["userinfo_url"], headers={
            "Authorization": f"Bearer {access}",
            "Accept": "application/vnd.github+json"}).json() or {}
        email = u.get("email")
        if not email:                       # private email → ask the emails API
            try:
                emails = cx.get("https://api.github.com/user/emails", headers={
                    "Authorization": f"Bearer {access}",
                    "Accept": "application/vnd.github+json"}).json() or []
                primary = next((e for e in emails
                                if e.get("primary") and e.get("verified")), None)
                email = (primary or (emails[0] if emails else {})).get("email")
            except Exception:
                pass
        return {"provider": "github", "sub": str(u.get("id") or ""),
                "email": email or "", "name": u.get("name") or u.get("login") or ""}

    # Google (OIDC userinfo)
    u = cx.get(cfg["userinfo_url"],
               headers={"Authorization": f"Bearer {access}"}).json() or {}
    return {"provider": "google", "sub": str(u.get("sub") or ""),
            "email": u.get("email") or "", "name": u.get("name") or ""}


def _wechat(cx, cfg, code) -> Optional[dict]:
    """WeChat: token via GET, no email, identity is the openid."""
    tok = cx.get(cfg["token_url"], params={
        "appid": cfg["client_id"], "secret": cfg["client_secret"],
        "code": code, "grant_type": "authorization_code"}).json() or {}
    access, openid = tok.get("access_token"), tok.get("openid")
    if not access or not openid:
        return None
    u = cx.get(cfg["userinfo_url"], params={
        "access_token": access, "openid": openid, "lang": "en"}).json() or {}
    return {"provider": "wechat", "sub": str(openid),
            "email": "", "name": u.get("nickname") or "WeChat user"}
