"""Session login for /admin and the CMS API. Accounts live in data/users.json."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from cms import accounts
from cms.paths import ROOT

LOGIN_HTML_PATH = Path(__file__).with_name("login.html")


def session_secret() -> str:
    explicit = os.environ.get("SESSION_SECRET", "").strip()
    if explicit:
        return explicit
    key_path = ROOT / "data" / "session.key"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    key_path.write_text(secret, encoding="utf-8")
    return secret


def current_user(request: Request) -> str | None:
    user = request.session.get("user")
    return user if user and accounts.get_user(user) else None


def is_authed(request: Request) -> bool:
    return current_user(request) is not None


def is_admin(request: Request) -> bool:
    name = current_user(request)
    if not name:
        return False
    record = accounts.get_user(name)
    return bool(record) and record.get("role") == "admin"


def safe_next(value: str | None) -> str:
    if value and value.startswith("/admin"):
        return value
    return "/admin/"


def login_page(error: bool = False, next_url: str = "/admin/") -> HTMLResponse:
    html_out = LOGIN_HTML_PATH.read_text(encoding="utf-8")
    html_out = html_out.replace("{{error}}", "display:block" if error else "display:none")
    html_out = html_out.replace("{{next}}", next_url.replace('"', "&quot;"))
    return HTMLResponse(html_out)


async def login_get(request: Request) -> Response:
    if is_authed(request):
        return RedirectResponse(safe_next(request.query_params.get("next")), status_code=302)
    return login_page(error=False, next_url=safe_next(request.query_params.get("next")))


async def login_post(request: Request) -> Response:
    form = await request.form()
    username = str(form.get("username") or "").strip()
    password = str(form.get("password") or "")
    next_url = safe_next(str(form.get("next") or request.query_params.get("next") or ""))
    user = accounts.authenticate(username, password)
    if user:
        request.session["user"] = user["username"]
        request.session["role"] = user["role"]
        return RedirectResponse(next_url, status_code=302)
    return login_page(error=True, next_url=next_url)


async def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


def unauthorized(request: Request) -> Response:
    if request.url.path.startswith("/cms-api"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    next_url = request.url.path
    if request.url.query:
        next_url += "?" + request.url.query
    return RedirectResponse("/login?" + urlencode({"next": next_url}), status_code=302)
