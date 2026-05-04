import runpy

from demos.integrations.claude_code.demo import *  # noqa: F401,F403


if __name__ == "__main__":
    runpy.run_module("demos.integrations.claude_code.demo", run_name="__main__")
