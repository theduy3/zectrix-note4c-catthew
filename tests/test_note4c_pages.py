import subprocess
import tempfile
import unittest
from pathlib import Path


class Note4CPageScheduleTests(unittest.TestCase):
    def test_daytime_rotation_night_window_and_wake_timer(self):
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "pages-test"
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            str(root / "tests/note4c_pages_test.cc"), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], text=True, capture_output=True, check=True)
            self.assertIn("NOTE4C_PAGES_OK", result.stdout)
