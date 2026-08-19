"""Regenerate HTML from JSON/markdown after a CMS save."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time

from cms.paths import ROOT

log = logging.getLogger("cms")
_lock = threading.Lock()


def rebuild_now() -> None:
    with _lock:
        started = time.monotonic()
        log.info("Rebuilding site…")
        subprocess.run(
            [sys.executable, str(ROOT / "build.py")],
            check=True,
            cwd=ROOT,
        )
        log.info("Rebuild finished in %.1fs", time.monotonic() - started)
