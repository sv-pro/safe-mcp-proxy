#!/usr/bin/env python3
"""One-click demo launcher for safe-mcp-proxy.

Usage:
    python run_demo.py [--port PORT]
"""
import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

_BASE = Path(__file__).resolve().parent

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _ensure_uvicorn() -> None:
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("Installing uvicorn…", flush=True)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "uvicorn", "--quiet"],
            check=True,
        )


def _wait_ready(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urlopen(f"{url}/stats", timeout=1)
            return True
        except (URLError, OSError):
            time.sleep(0.3)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch safe-mcp-proxy demo")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    _ensure_uvicorn()

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", args.host,
            "--port", str(args.port),
            "--no-access-log",
        ],
        cwd=str(_BASE),
    )

    print(f"Starting safe-mcp-proxy at {url} …", flush=True)

    if not _wait_ready(url):
        proc.terminate()
        sys.exit("Server did not become ready in time.")

    print(f"Ready → {url}", flush=True)
    webbrowser.open(url)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down…", flush=True)
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
