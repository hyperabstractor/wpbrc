"""WPBRC site + Decap filesystem proxy.

Public pages are static files. /admin and /cms-api/v1 require a session from
/login. Saving in Decap writes JSON/markdown on disk and runs build.py.
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from cms import accounts, auth, proxy, user_admin
from cms.paths import ROOT, UnsafePath

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("cms")

accounts.bootstrap()

# Coolify terminates TLS in front of the container. Set CMS_HTTPS=1 so the
# login cookie is marked Secure. Leave it off for local http://localhost.
HTTPS_ONLY = os.environ.get("CMS_HTTPS", "0") == "1"


class AuthGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/admin") or path.startswith("/cms-api"):
            if not auth.is_authed(request):
                return auth.unauthorized(request)
        return await call_next(request)


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if path.startswith("/admin") or path.startswith("/cms-api") or path.startswith("/login"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; "
                "connect-src 'self' https:; img-src 'self' https: data: blob:"
            )
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
                "connect-src 'self' https://*.tile.openstreetmap.org https://registry.npmjs.org; "
                "frame-src https://www.zeffy.com https://*.zeffy.com; "
                "form-action 'self' https://formsubmit.co; base-uri 'self'; object-src 'none'",
            )
        return response


app = FastAPI(title="WPBRC CMS", docs_url=None, redoc_url=None, openapi_url=None)

# Last added runs first — session must wrap the auth gate so /admin can read the cookie.
app.add_middleware(AuthGate)
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.session_secret(),
    same_site="lax",
    https_only=HTTPS_ONLY,
)
app.add_middleware(SecurityHeaders)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


app.add_api_route("/login", auth.login_get, methods=["GET"])
app.add_api_route("/login", auth.login_post, methods=["POST"])
app.add_api_route("/logout", auth.logout, methods=["GET"])
app.add_api_route("/admin/users", user_admin.users_get, methods=["GET"])
app.add_api_route("/admin/users", user_admin.users_post, methods=["POST"])
app.add_api_route("/admin/users/delete", user_admin.users_delete, methods=["POST"])


@app.post("/cms-api/v1")
async def cms_api(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    action = body.get("action")
    params = body.get("params") if isinstance(body.get("params"), dict) else {}
    try:
        result = await asyncio.to_thread(proxy.handle, action, params)
        return JSONResponse(content=result)
    except UnsafePath as e:
        log.warning("Rejected path: %s", e)
        return JSONResponse({"error": "invalid path"}, status_code=400)
    except FileNotFoundError:
        return JSONResponse({"error": "not found"}, status_code=404)
    except KeyError:
        return JSONResponse({"error": f"Unknown action {action}"}, status_code=422)
    except Exception:
        log.exception("CMS action %s failed", action)
        return JSONResponse({"error": "Unknown error"}, status_code=500)


class _SiteFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if path.startswith("assets/"):
            response.headers.setdefault("Cache-Control", "public, max-age=604800")
        return response


app.mount("/", _SiteFiles(directory=str(ROOT), html=True), name="site")
log.info("WPBRC CMS serving %s", ROOT)
