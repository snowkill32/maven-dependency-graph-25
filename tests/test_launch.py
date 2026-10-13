"""Интеграционные проверки настоящего процесса Python."""

from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUCCESS = 0
CLI_ERROR = 2


class LaunchTests(unittest.TestCase):
    """Проверить вывод и коды завершения точки входа."""

    def run_cli(self, arguments):
        """Запустить CLI отдельным процессом с UTF-8 выводом."""
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "src", *arguments],
            cwd=PROJECT_ROOT, text=True, encoding="utf-8",
            capture_output=True, check=False,
        )

    def test_successful_process(self):
        """CLI выводит ожидаемые значения и не пишет ошибок."""
        result = self.run_cli([
            "--package", "A", "--repository", "examples/repository.json",
            "--test-mode", "--ascii-tree",
        ])
        self.assertEqual(result.returncode, SUCCESS)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "package=A\nrepository=examples/repository.json\n"
            "test_mode=true\nascii_tree=true\n",
        )

    def test_failed_process(self):
        """Ошибочный запуск завершается с 2 без Python traceback."""
        result = self.run_cli([
            "--package", "org.example:demo:1.0",
            "--repository", "not-a-url",
        ])
        self.assertEqual(result.returncode, CLI_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("--repository", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
