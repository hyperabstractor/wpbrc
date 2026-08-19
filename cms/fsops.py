"""Read / write / list files for the Decap proxy protocol."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cms.paths import UnsafePath, rel_posix, safe_path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_entry(rel: str) -> dict:
    try:
        path = safe_path(rel)
        data = path.read_bytes()
        return {
            "data": data.decode("utf-8"),
            "file": {"path": rel_posix(path), "id": sha256_bytes(data)},
        }
    except (OSError, UnicodeDecodeError):
        return {"data": None, "file": {"path": rel.replace("\\", "/"), "id": None}}
    except UnsafePath:
        raise


def write_file(rel: str, content: bytes) -> Path:
    path = safe_path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return path


def delete_file(rel: str) -> None:
    path = safe_path(rel)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def move_file(src_rel: str, dest_rel: str) -> None:
    src = safe_path(src_rel)
    dest = safe_path(dest_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.replace(dest)


def list_files(folder: str, extension: str, depth: int) -> list[str]:
    """Return posix paths relative to SITE_ROOT, matching Decap's localFs listing."""
    if depth <= 0:
        return []
    try:
        base = safe_path(folder)
    except UnsafePath:
        return []
    if not base.is_dir():
        return []

    def matches(name: str) -> bool:
        if name.startswith(".") or name.endswith(".tmp"):
            return False
        if not extension:
            return True
        return name.endswith(extension) or name.endswith(f".{extension.lstrip('.')}")

    out: list[str] = []

    def walk(dirpath: Path, remaining: int) -> None:
        if remaining <= 0:
            return
        try:
            entries = sorted(dirpath.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        for ent in entries:
            if ent.name.startswith("."):
                continue
            if ent.is_dir():
                walk(ent, remaining - 1)
            elif ent.is_file() and matches(ent.name):
                out.append(rel_posix(ent))

    walk(base, depth)
    return out


def read_media(rel: str) -> dict:
    path = safe_path(rel)
    data = path.read_bytes()
    return {
        "id": sha256_bytes(data),
        "content": base64.b64encode(data).decode("ascii"),
        "encoding": "base64",
        "path": rel_posix(path),
        "name": path.name,
    }
