"""Run Bloom API using the local src tree explicitly.

This bypasses stale site-packages imports by prepending ./src to sys.path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bloom import main as bloom_main  # noqa: E402


if __name__ == "__main__":
    host = os.getenv("BLOOM_HOST", "0.0.0.0")
    port = int(os.getenv("BLOOM_PORT", "8000"))
    print(f"[serve_local] using module: {bloom_main.__file__}")
    uvicorn.run(bloom_main.app, host=host, port=port)
