"""Проверки точки входа через настоящий процесс Python."""

from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LaunchTests(unittest.TestCase):
    """Коды завершения и разделение stdout/stderr при запуске приложения."""

    def run_cli(self, arguments):
        """Запустить приложение в корне проекта с выводом UTF-8."""
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "src", *arguments],
            cwd=PROJECT_ROOT, text=True, encoding="utf-8",
            capture_output=True, check=False,
        )

    def test_test_mode_process(self):
        """Тестовый режим печатает все четыре значения и не пишет ошибок."""
        result = self.run_cli([
            "--package", "A", "--repository", "examples/repository.json",
            "--test-mode", "--ascii-tree",
        ])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout,
                         "package=A\nrepository=examples/repository.json\n"
                         "test_mode=true\nascii_tree=true\n")

    def test_invalid_configuration_process(self):
        """Неверный URL дает код 2, stderr и пустой stdout без traceback."""
        result = self.run_cli([
            "--package", "g:app:1", "--repository", "not-a-url",
        ])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--repository", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
