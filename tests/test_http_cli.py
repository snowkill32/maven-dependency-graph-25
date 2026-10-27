"""Проверка CLI с настоящим локальным HTTP-репозиторием Maven."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from threading import Thread
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


class RecordingHandler(SimpleHTTPRequestHandler):
    """Раздать тестовые POM и сохранить список запросов для проверки."""

    def do_GET(self):
        """Записать адрес и передать обработку встроенному HTTP-серверу."""
        self.server.request_paths.append(self.path)
        super().do_GET()

    def log_message(self, format_string, *arguments):
        """Не засорять вывод тестов журналом HTTP-сервера."""
        return None


class HttpCliTests(unittest.TestCase):
    """Полный путь от аргументов до HTTP, XML и вывода пользователю."""

    def setUp(self):
        """Запустить сервер на свободном локальном порту."""
        handler = partial(RecordingHandler, directory=str(FIXTURES))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.request_paths = []
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        port = self.server.server_port
        self.repository = f"http://127.0.0.1:{port}/maven2/"

    def stop_server(self):
        """Остановить HTTP-сервер и дождаться освобождения порта."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_cli(self, package):
        """Запустить реальное приложение с локальным адресом репозитория."""
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "src", "--package", package,
             "--repository", self.repository],
            cwd=PROJECT_ROOT, text=True, encoding="utf-8",
            capture_output=True, check=False,
        )

    def test_parent_bom_and_no_transitive_requests(self):
        """Версии берутся из POM/родителя/BOM без запроса самих зависимостей."""
        result = self.run_cli("g:app:1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout,
                         "Прямые зависимости g:app:1:\n"
                         "- g:lib:2.5 [scope=compile, type=jar, "
                         "optional=false]\n"
                         "- g:managed:3 [scope=runtime, type=jar, "
                         "optional=false]\n"
                         "- g:test-helper:4 [scope=test, type=jar, "
                         "optional=true]\n")
        self.assertEqual(set(self.server.request_paths), {
            "/maven2/g/app/1/app-1.pom",
            "/maven2/g/parent/1/parent-1.pom",
            "/maven2/g/bom/1/bom-1.pom",
        })

    def test_empty_package(self):
        """Пакет без зависимостей обрабатывается как успешный результат."""
        result = self.run_cli("g:empty:1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Прямых зависимостей нет.", result.stdout)

    def test_missing_package(self):
        """Настоящий HTTP 404 завершается с 1 и понятным сообщением."""
        result = self.run_cli("g:missing:1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("не найден", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_pom(self):
        """Ошибка XML из HTTP-ответа не приводит к Python traceback."""
        result = self.run_cli("g:broken:1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("XML", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
