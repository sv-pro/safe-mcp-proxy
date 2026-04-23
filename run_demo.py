#!/usr/bin/env python3
"""One-click launcher: starts the safe-mcp-proxy API and opens the UI in a browser.

Usage:
    python run_demo.py
"""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

HOST = "http://localhost:8000"
BASE_DIR = Path(__file__).resolve().parent


def _server_ready(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=1)
        return True
    except Exception:
        return False


def _wait_ready(url: str, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _server_ready(url):
            return True
        time.sleep(0.5)
    return False


if __name__ == "__main__":
    print("safe-mcp-proxy — starting server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(BASE_DIR),
    )
    try:
        print(f"Waiting for {HOST} ...", end="", flush=True)
        if _wait_ready(HOST):
            print(" ready")
            webbrowser.open(HOST)
            print(f"UI open at {HOST}  (Ctrl+C to stop)")
            proc.wait()
        else:
            print(" timed out")
            proc.terminate()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc.terminate()
