"""python -m cms  →  uvicorn on $PORT (default 8080)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("cms.app:app", host="0.0.0.0", port=port, reload=os.environ.get("CMS_RELOAD") == "1")


if __name__ == "__main__":
    main()
