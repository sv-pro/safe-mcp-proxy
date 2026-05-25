import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src/main/python"))

from demos.product.dashboard.web_launcher import _ensure_uvicorn, _wait_ready, main

if __name__ == "__main__":
    main()
