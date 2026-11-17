"""Повторяемые границы публикации; отдельный Python loader в каждой ветке."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'evaluation/task04/check_recovery.py'
spec = importlib.util.spec_from_file_location('recovery_task04', PATH)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def test_focused_windows_publication_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            results = recovery.run_scenarios(Path(folder))
            self.assertTrue(all(r['passed'] for r in results.values()))


if __name__ == '__main__':
    unittest.main()
