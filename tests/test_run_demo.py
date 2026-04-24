import subprocess
import sys
import unittest


class TestRunDemo(unittest.TestCase):
    def test_wait_ready_returns_false_on_closed_port(self):
        import run_demo
        # Port 19999 should not be listening; must time out quickly.
        ready = run_demo._wait_ready("http://127.0.0.1:19999", timeout=0.5)
        self.assertFalse(ready)

    def test_ensure_uvicorn_is_noop_when_installed(self):
        import run_demo
        # uvicorn is already installed; should not raise.
        run_demo._ensure_uvicorn()

    def test_script_help_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, "run_demo.py", "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--port", result.stdout)
