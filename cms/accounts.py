"""Editor accounts stored on disk. Admins add people from /admin/users — no public signup."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
from pathlib import Path

from cms.paths import ROOT

USERS_PATH = Path(os.environ.get("CMS_USERS_FILE", ROOT / "data" / "users.json"))
_lock = threading.Lock()
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{2,32}$")
ROLES = ("admin", "editor")


class AccountError(ValueError):
    pass


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    rounds = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2${rounds}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        kind, rounds, salt_hex, hash_hex = stored.split("$", 3)
        if kind != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return secrets.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def _load() -> list[dict]:
    if not USERS_PATH.exists():
        return []
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    users = data.get("users") if isinstance(data, dict) else None
    return users if isinstance(users, list) else []


def _save(users: list[dict]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"users": users}, indent=2) + "\n", encoding="utf-8")
    tmp.replace(USERS_PATH)


def list_users() -> list[dict]:
    with _lock:
        return [
            {"username": u.get("username", ""), "role": u.get("role") or "editor"}
            for u in _load()
            if u.get("username")
        ]


def get_user(username: str) -> dict | None:
    want = username.strip().lower()
    with _lock:
        for u in _load():
            if str(u.get("username", "")).lower() == want:
                return u
    return None


def authenticate(username: str, password: str) -> dict | None:
    user = get_user(username)
    if not user:
        return None
    if not _verify_password(password, str(user.get("password") or "")):
        return None
    return {"username": user["username"], "role": user.get("role") or "editor"}


def add_user(username: str, password: str, role: str = "editor") -> dict:
    username = username.strip()
    role = role if role in ROLES else "editor"
    if not USERNAME_RE.match(username):
        raise AccountError("Username must be 2–32 letters, numbers, dots, hyphens, or underscores.")
    if len(password) < 8:
        raise AccountError("Password must be at least 8 characters.")
    with _lock:
        users = _load()
        if any(str(u.get("username", "")).lower() == username.lower() for u in users):
            raise AccountError("That username is already taken.")
        record = {"username": username, "password": _hash_password(password), "role": role}
        users.append(record)
        _save(users)
    return {"username": username, "role": role}


def delete_user(username: str, *, acting: str) -> None:
    username = username.strip()
    if username.lower() == acting.strip().lower():
        raise AccountError("You cannot delete your own account.")
    with _lock:
        users = _load()
        remaining = [u for u in users if str(u.get("username", "")).lower() != username.lower()]
        if len(remaining) == len(users):
            raise AccountError("No user with that username.")
        admins = [u for u in remaining if u.get("role") == "admin"]
        if not admins:
            raise AccountError("Cannot delete the last admin.")
        _save(remaining)


def _env_seed() -> list[tuple[str, str, str]]:
    """First env user is admin; any CMS_USERS extras are editors."""
    raw = os.environ.get("CMS_USERS", "").strip()
    if raw:
        out: list[tuple[str, str, str]] = []
        for i, part in enumerate(raw.split(",")):
            if ":" not in part:
                continue
            name, password = part.split(":", 1)
            name, password = name.strip(), password.strip()
            if name and password:
                out.append((name, password, "admin" if i == 0 else "editor"))
        return out
    user = os.environ.get("CMS_USER", "admin").strip() or "admin"
    password = os.environ.get("CMS_PASSWORD", "").strip()
    if not password:
        return []
    return [(user, password, "admin")]


def bootstrap() -> None:
    """Create data/users.json from env if it does not exist yet."""
    with _lock:
        if _load():
            return
        seed = _env_seed()
        if not seed:
            raise SystemExit(
                "No editor accounts yet. Set CMS_PASSWORD (optional CMS_USER) or CMS_USERS="
                "admin:pass,editor:pass2 for the first run. After that, add people at /admin/users."
            )
        users = [
            {"username": name, "password": _hash_password(pw), "role": role}
            for name, pw, role in seed
        ]
        _save(users)
