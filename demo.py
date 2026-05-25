import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src/main/python"))

import runpy
if __name__ == "__main__":
    runpy.run_module("demos.core.demo_all", run_name="__main__")
