"""Запуск настоящего CLI с локальным HTTP-репозиторием Maven."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from threading import Thread
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "maven2"


class RepositoryHandler(SimpleHTTPRequestHandler):
    """Отдавать POM из тестовой папки и записывать запрошенные пути."""

    paths = []

    def do_GET(self):
        """Запомнить HTTP-запрос перед стандартной обработкой файла."""
        self.paths.append(self.path)
        return super().do_GET()

    def log_message(self, format, *args):
        """Подавить журнал HTTP, чтобы он не смешивался с отчетом тестов."""
        return


class HttpCliTests(unittest.TestCase):
    """Проверить загрузку, парсер и CLI вместе без внешних сервисов."""

    def setUp(self):
        """Поднять HTTP-сервер на свободном локальном порту."""
        RepositoryHandler.paths = []
        handler = partial(RepositoryHandler, directory=str(FIXTURES))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}/"

    def stop_server(self):
        """Завершить поток и освободить порт после проверки."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_cli(self, package):
        """Выполнить точку входа отдельным процессом с тайм-аутом."""
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "src", "--package", package,
             "--repository", self.base],
            cwd=PROJECT_ROOT, text=True, encoding="utf-8",
            capture_output=True, timeout=10, check=False,
        )

    def test_dependencies_with_parent_and_bom(self):
        """Граф содержит общий узел и цикл, POM загружаются в BFS-порядке."""
        result = self.run_cli("g:app:1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout,
                         "Граф зависимостей g:app:1:\n"
                         "Порядок обхода BFS: g:app:1, g:test-library:4, "
                         "g:library:2.5, g:extension:3.1, g:shared:1\n"
                         "g:app:1 -> g:test-library:4, g:library:2.5, "
                         "g:extension:3.1\n"
                         "g:test-library:4 -> g:shared:1\n"
                         "g:library:2.5 -> g:shared:1\n"
                         "g:extension:3.1 -> g:app:1\n"
                         "g:shared:1 -> (нет зависимостей)\n")
        self.assertEqual(RepositoryHandler.paths, [
            "/g/app/1/app-1.pom", "/g/parent/1/parent-1.pom",
            "/g/bom/1/bom-1.pom",
            "/g/test-library/4/test-library-4.pom",
            "/g/library/2.5/library-2.5.pom",
            "/g/extension/3.1/extension-3.1.pom", "/g/shared/1/shared-1.pom",
        ])

    def test_empty_dependencies(self):
        """Пустой список успешно выводится в настоящем процессе."""
        result = self.run_cli("g:empty:1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("нет зависимостей", result.stdout)

    def test_missing_transitive_pom(self):
        """Ошибка глубже корня не приводит к печати незавершенного графа."""
        result = self.run_cli("g:incomplete:1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("g:missing:1", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_http_and_xml_errors(self):
        """404 и поврежденный POM дают stderr и код 1 без traceback."""
        for package, message in (("g:missing:1", "не найден"),
                                 ("g:broken:1", "XML POM")):
            with self.subTest(package=package):
                result = self.run_cli(package)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
