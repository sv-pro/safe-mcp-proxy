import runpy

from demos.product.dashboard.demo import *  # noqa: F401,F403


if __name__ == "__main__":
    runpy.run_module("demos.product.dashboard.demo", run_name="__main__")
