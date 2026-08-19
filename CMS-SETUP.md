# No-code editing (CMS) — setup & use

Board members edit content at **/admin/** through simple web forms — no coding
and no GitHub. The editor is Decap CMS. A small Python server in `cms/` writes
those changes to files on disk and runs `python3 build.py` so the public pages
update.

## What editors can change from /admin/
- 🗺️ **Development Tracker** — add/update projects and statuses (the map).
- 👥 **Board of Directors** — names, roles, neighborhood, years in WPB, bios.
- 📌 **Current Issues** — the six issues and all their fields.
- 📅 **Calendar / Events** — upcoming meetings and events.
- 📰 **Media / Press** — coverage entries.
- 🏘️ **Neighborhood Directory** — the associations list.

## How updates flow
1. An editor signs in at `wpbrc.org/login` with their own username + password.
2. They edit at `/admin/editor.html` and click **Save**.
3. The proxy writes `assets/*.json` / `content/**` on the server.
4. `build.py` regenerates the HTML — live in a few seconds.

Admins add people at `/admin/users` (no public registration). The first admin is
created from `CMS_USER` / `CMS_PASSWORD` on first start; after that the list lives
in `data/users.json`.

## Local development
From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CMS_PASSWORD=devpassword CMS_HTTPS=0
python3 -m cms
```

Open http://localhost:8080/login (user `admin`, password `devpassword`).

Or: `CMS_PASSWORD=devpassword docker compose up --build`

## Coolify
1. New resource → Dockerfile (this repo). Port `8080` (or `$PORT`).
2. Set env: `CMS_USER`, `CMS_PASSWORD`, `SESSION_SECRET`, `CMS_HTTPS=1`.
3. Persist `/app/assets`, `/app/content`, `/app/drafts`, and `/app/data` so CMS saves and editor accounts survive redeploys.
4. Point `wpbrc.org` at the Coolify app.

Health check: `GET /healthz`.

## Editing tips
- **Map coordinates:** right-click the building in Google Maps, copy lat/long.
- **IDs must be unique** and lowercase-with-dashes (e.g. `one-flagler`).
- **Images:** uploads go to `assets/uploads/`.
- There is no GitHub history from the editor. Keep backups of the persisted folders.
