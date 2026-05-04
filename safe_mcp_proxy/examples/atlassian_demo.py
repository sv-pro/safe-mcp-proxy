import runpy

from demos.integrations.atlassian.demo import *  # noqa: F401,F403


if __name__ == "__main__":
    runpy.run_module("demos.integrations.atlassian.demo", run_name="__main__")
