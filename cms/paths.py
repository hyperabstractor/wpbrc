"""Resolve CMS write paths and refuse anything outside the content dirs."""

from __future__ import annotations

import os
from pathlib import Path

# Repo root (parent of cms/) unless SITE_ROOT is set.
ROOT = Path(os.environ.get("SITE_ROOT", Path(__file__).resolve().parent.parent)).resolve()

# Decap may only touch content — never cms/, tools/, or server code.
ALLOWED_ROOTS = ("assets", "content", "drafts")


class UnsafePath(ValueError):
    pass


def _clean_rel(rel: str) -> str:
    if not rel or not isinstance(rel, str):
        raise UnsafePath("empty path")
    rel = rel.replace("\\", "/").lstrip("/")
    if rel.startswith("/") or ":" in rel.split("/")[0]:
        raise UnsafePath(rel)
    parts = [p for p in rel.split("/") if p and p != "."]
    if not parts or ".." in parts:
        raise UnsafePath(rel)
    if parts[0] not in ALLOWED_ROOTS:
        raise UnsafePath(rel)
    return "/".join(parts)


def safe_path(rel: str) -> Path:
    """Return an absolute path under SITE_ROOT, or raise UnsafePath."""
    cleaned = _clean_rel(rel)
    full = (ROOT / cleaned).resolve()
    if not full.is_relative_to(ROOT):
        raise UnsafePath(rel)
    return full


def rel_posix(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()
