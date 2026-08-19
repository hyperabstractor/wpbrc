"""Admin-only page to add and remove editor accounts."""

from __future__ import annotations

import html
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from cms import accounts
from cms.auth import current_user, is_admin

TEMPLATE = Path(__file__).with_name("users.html")


def _page(request: Request, error: str = "", notice: str = "") -> HTMLResponse:
    who = html.escape(current_user(request) or "")
    rows = []
    for u in accounts.list_users():
        name = html.escape(u["username"])
        role = html.escape(u["role"])
        you = u["username"] == current_user(request)
        delete = (
            "<span style=\"color:var(--muted);font-size:12.5px\">you</span>"
            if you
            else (
                f'<form method="post" action="/admin/users/delete" style="margin:0" '
                f'onsubmit="return confirm(\'Remove {name}?\')">'
                f'<input type="hidden" name="username" value="{name}">'
                f'<button class="danger" type="submit">Remove</button></form>'
            )
        )
        rows.append(f"<tr><td>{name}</td><td><span class=\"pill\">{role}</span></td><td>{delete}</td></tr>")
    html_out = TEMPLATE.read_text(encoding="utf-8")
    html_out = html_out.replace("{{who}}", who)
    html_out = html_out.replace("{{error}}", html.escape(error))
    html_out = html_out.replace("{{notice}}", html.escape(notice))
    html_out = html_out.replace("{{error_display}}", "display:block" if error else "display:none")
    html_out = html_out.replace("{{notice_display}}", "display:block" if notice else "display:none")
    html_out = html_out.replace("{{rows}}", "\n".join(rows) or "<tr><td colspan=3>No users yet.</td></tr>")
    return HTMLResponse(html_out)


def _deny() -> Response:
    return HTMLResponse(
        "<!doctype html><p>Only admins can manage editors. <a href='/admin/'>Back</a></p>",
        status_code=403,
    )


async def users_get(request: Request) -> Response:
    if not is_admin(request):
        return _deny()
    return _page(request)


async def users_post(request: Request) -> Response:
    if not is_admin(request):
        return _deny()
    form = await request.form()
    try:
        created = accounts.add_user(
            str(form.get("username") or ""),
            str(form.get("password") or ""),
            str(form.get("role") or "editor"),
        )
    except accounts.AccountError as e:
        return _page(request, error=str(e))
    return _page(request, notice=f"Added {created['username']} ({created['role']}).")


async def users_delete(request: Request) -> Response:
    if not is_admin(request):
        return _deny()
    form = await request.form()
    acting = current_user(request) or ""
    try:
        accounts.delete_user(str(form.get("username") or ""), acting=acting)
    except accounts.AccountError as e:
        return _page(request, error=str(e))
    return RedirectResponse("/admin/users", status_code=303)
