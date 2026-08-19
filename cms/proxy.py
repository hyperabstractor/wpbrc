"""Decap CMS proxy protocol: one POST /cms-api/v1 with {action, params}."""

from __future__ import annotations

import base64

from cms.fsops import delete_file, list_files, move_file, read_entry, read_media, write_file
from cms.paths import ROOT
from cms.rebuild import rebuild_now


def _b64_bytes(content: str, encoding: str) -> bytes:
    if encoding != "base64":
        raise ValueError(f"unsupported encoding {encoding!r}")
    return base64.b64decode(content)


def handle(action: str, params: dict | None) -> object:
    params = params or {}

    if action == "info":
        return {"repo": ROOT.name, "publish_modes": ["simple"], "type": "local_fs"}

    if action == "getEntry":
        return read_entry(params["path"])

    if action == "entriesByFiles":
        files = params.get("files") or []
        return [read_entry(f["path"] if isinstance(f, dict) else f) for f in files]

    if action == "entriesByFolder":
        folder = params.get("folder") or ""
        extension = params.get("extension") or ""
        depth = int(params.get("depth") or 1)
        return [read_entry(rel) for rel in list_files(folder, extension, depth)]

    if action == "persistEntry":
        data_files = params.get("dataFiles")
        if not data_files:
            entry = params.get("entry")
            data_files = [entry] if entry else []
        assets = params.get("assets") or []
        for df in data_files:
            raw = df.get("raw")
            if raw is None:
                continue
            write_file(df["path"], raw.encode("utf-8") if isinstance(raw, str) else raw)
        for asset in assets:
            write_file(asset["path"], _b64_bytes(asset.get("content") or "", asset.get("encoding") or "base64"))
        for df in data_files:
            new_path = df.get("newPath")
            if new_path and new_path != df.get("path"):
                move_file(df["path"], new_path)
        rebuild_now()
        return {"message": "entry persisted"}

    if action == "getMedia":
        folder = params.get("mediaFolder") or "assets/uploads"
        out = []
        for rel in list_files(folder, "", 1):
            try:
                out.append(read_media(rel))
            except (OSError, UnsafePath):
                continue
        return out

    if action == "getMediaFile":
        return read_media(params["path"])

    if action == "persistMedia":
        asset = params.get("asset") or {}
        rel = asset["path"]
        write_file(rel, _b64_bytes(asset.get("content") or "", asset.get("encoding") or "base64"))
        rebuild_now()
        return read_media(rel)

    if action == "deleteFile":
        delete_file(params["path"])
        rebuild_now()
        return {"message": f"deleted file {params['path']}"}

    if action == "deleteFiles":
        paths = params.get("paths") or []
        for rel in paths:
            delete_file(rel)
        rebuild_now()
        return {"message": f"deleted files {', '.join(paths)}"}

    if action == "getDeployPreview":
        return None

    if action == "unpublishedEntries":
        return []

    if action in {
        "unpublishedEntry",
        "unpublishedEntryDataFile",
        "unpublishedEntryMediaFile",
        "deleteUnpublishedEntry",
        "updateUnpublishedEntryStatus",
        "publishUnpublishedEntry",
    }:
        raise FileNotFoundError("editorial workflow is not used")

    if action == "getNotes":
        return {"notes": []}

    if action == "getPRMetadata":
        return {"metadata": None}

    raise KeyError(action)
