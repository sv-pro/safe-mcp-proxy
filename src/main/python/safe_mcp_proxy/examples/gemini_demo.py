import runpy

from demos.integrations.gemini.demo import *  # noqa: F401,F403


if __name__ == "__main__":
    runpy.run_module("demos.integrations.gemini.demo", run_name="__main__")
