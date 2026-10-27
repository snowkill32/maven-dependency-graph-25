"""Проверка пользовательских параметров и обработки ошибок CLI."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.cli import format_config, format_dependencies, main, parse_config
from src.config import Config
from src.pom import Dependency


class CliTests(unittest.TestCase):
    """Проверки успешных запусков и ошибок всех четырех параметров."""

    def setUp(self):
        """Создать отдельный тестовый репозиторий для каждого теста."""
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.repository = self.directory / "test repository.json"
        self.repository.write_text('{"A": ["B"], "B": []}', encoding="utf-8")
        self.normal_args = [
            "--package", "org.example:demo:1.0",
            "--repository", "https://example.org/maven2/",
        ]
        self.test_args = [
            "--package", "A", "--repository", str(self.repository),
            "--test-mode",
        ]

    def assert_cli_error(self, arguments, expected):
        """Проверить код 2, сообщение в stderr и отсутствие результата."""
        error_output, output = StringIO(), StringIO()
        with redirect_stderr(error_output), redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(arguments)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn(expected, error_output.getvalue())
        self.assertEqual(output.getvalue(), "")

    def test_normal_config(self):
        """В обычном режиме флаги по умолчанию выключены."""
        config = parse_config(self.normal_args)
        self.assertEqual(config.package, "org.example:demo:1.0")
        self.assertEqual(config.repository, "https://example.org/maven2/")
        self.assertFalse(config.test_mode)
        self.assertFalse(config.ascii_tree)

    def test_test_config(self):
        """Локальный путь с пробелами и оба флага принимаются."""
        config = parse_config(self.test_args + ["--ascii-tree"])
        self.assertEqual(config.package, "A")
        self.assertEqual(config.repository, str(self.repository))
        self.assertTrue(config.test_mode)
        self.assertTrue(config.ascii_tree)

    def test_ascii_flag_in_normal_mode(self):
        """ASCII-флаг можно включить без тестового режима."""
        config = parse_config(self.normal_args + ["--ascii-tree"])
        self.assertTrue(config.ascii_tree)

    def test_key_value_format(self):
        """Вывод содержит ровно четыре настройки с понятными значениями."""
        config = Config("A", "repo.json", True, False)
        self.assertEqual(
            format_config(config),
            "package=A\nrepository=repo.json\ntest_mode=true\nascii_tree=false",
        )

    def test_main_output(self):
        """Обычный запуск печатает список зависимостей вместо конфигурации."""
        output = StringIO()
        with patch("src.cli.get_direct_dependencies", return_value=[]):
            with redirect_stdout(output):
                self.assertEqual(main(self.normal_args), 0)
        self.assertEqual(output.getvalue(),
                         "Прямые зависимости org.example:demo:1.0:\n"
                         "Прямых зависимостей нет.\n")

    def test_test_mode_keeps_configuration_output(self):
        """Тестовый режим пока проверяет только параметры первого этапа."""
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(self.test_args), 0)
        expected = format_config(parse_config(self.test_args)) + "\n"
        self.assertEqual(output.getvalue(), expected)

    def test_runtime_failure(self):
        """Ошибка получения POM дает код 1 и не оставляет частичный вывод."""
        output, errors = StringIO(), StringIO()
        with patch("src.cli.get_direct_dependencies",
                   side_effect=ValueError("POM не найден")):
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(main(self.normal_args), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("POM не найден", errors.getvalue())

    def test_dependency_output_includes_scope_optional_and_classifier(self):
        """Вывод различает тестовые и необязательные зависимости."""
        dependency = Dependency("g", "lib", "2", "test", "test-jar",
                                "tests", "true")
        self.assertEqual(
            format_dependencies("g:app:1", [dependency]),
            "Прямые зависимости g:app:1:\n"
            "- g:lib:2 [scope=test, type=test-jar, classifier=tests, "
            "optional=true]",
        )

    def test_ascii_flag_does_not_hide_direct_dependencies(self):
        """Настройка будущего дерева сохраняет плоский список этапа 2."""
        output = StringIO()
        dependency = Dependency("g", "lib", "2", "compile", "jar", "",
                                "false")
        with patch("src.cli.get_direct_dependencies",
                   return_value=[dependency]):
            with redirect_stdout(output):
                self.assertEqual(main(self.normal_args + ["--ascii-tree"]), 0)
        self.assertIn("g:lib:2", output.getvalue())

    def test_help(self):
        """Справка описывает все четыре опции и завершается с 0."""
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        for option in ("--package", "--repository", "--test-mode",
                       "--ascii-tree"):
            self.assertIn(option, output.getvalue())

    def test_missing_required_options(self):
        """Обе обязательные настройки нужны для запуска."""
        cases = [([], "--package"),
                 (["--repository", "https://example.org"], "--package"),
                 (["--package", "org.example:demo:1.0"], "--repository")]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                self.assert_cli_error(arguments, expected)

    def test_options_without_values(self):
        """Опции пакета и репозитория требуют значения."""
        for option in ("--package", "--repository"):
            with self.subTest(option=option):
                self.assert_cli_error(self.normal_args + [option], option)

    def test_invalid_maven_names(self):
        """Пустое имя, пробелы и неверные координаты отклоняются."""
        for package in ("", "demo", "a:b", "a::1", "a:b:1:extra",
                        "a b:c:1", "../a:b:1"):
            with self.subTest(package=package):
                arguments = self.normal_args.copy()
                arguments[1] = package
                self.assert_cli_error(arguments, "--package")

    def test_invalid_test_names(self):
        """Для тестового режима допустима одна большая латинская буква."""
        for package in ("", "a", "AA", "1", "А", "a:b:1"):
            with self.subTest(package=package):
                arguments = self.test_args.copy()
                arguments[1] = package
                self.assert_cli_error(arguments, "--package")

    def test_valid_urls(self):
        """Поддерживаются HTTP(S), локальный сервер, порт и IPv6."""
        for url in ("http://localhost:8080/repo", "https://example.org",
                    "http://[::1]:8080/repo"):
            with self.subTest(url=url):
                arguments = self.normal_args.copy()
                arguments[3] = url
                self.assertEqual(parse_config(arguments).repository, url)

    def test_invalid_urls(self):
        """Неверная схема, сервер, порт и посторонние части URL запрещены."""
        urls = ("", " ", "repo.json", "ftp://example.org", "https://",
                "https://bad host/repo", "https://!!!/repo",
                "https://example.org:abc", "https://example.org:70000",
                "https://example.org:0", "https://[broken",
                "https://user:password@example.org",
                "https://example.org?x=1", "https://example.org#fragment")
        for url in urls:
            with self.subTest(url=url):
                arguments = self.normal_args.copy()
                arguments[3] = url
                self.assert_cli_error(arguments, "--repository")

    def test_invalid_file_paths(self):
        """Пустой путь, отсутствующий файл и каталог отклоняются."""
        for path in ("", " ", str(self.directory / "missing.json"),
                     str(self.directory), "https://example.org"):
            with self.subTest(path=path):
                arguments = self.test_args.copy()
                arguments[3] = path
                self.assert_cli_error(arguments, "--repository")

    def test_non_utf8_file(self):
        """Файл с неподходящей кодировкой дает понятную ошибку."""
        self.repository.write_bytes(b"\xff\xfe")
        self.assert_cli_error(self.test_args, "UTF-8")

    def test_unreadable_file(self):
        """Ошибка доступа обрабатывается без трассировки исключения."""
        with patch("src.config.Path.read_text", side_effect=PermissionError):
            self.assert_cli_error(self.test_args, "доступен для чтения")

    def test_flags_reject_values(self):
        """Флаги включаются присутствием и не принимают true/false."""
        for option in ("--test-mode", "--ascii-tree"):
            for value in ("true", "false", "123"):
                with self.subTest(option=option, value=value):
                    self.assert_cli_error(
                        self.normal_args + [f"{option}={value}"], option,
                    )

    def test_unknown_and_abbreviated_options(self):
        """Неизвестные и сокращенные опции не принимаются."""
        for option in ("--unknown", "--test", "--ascii"):
            with self.subTest(option=option):
                self.assert_cli_error(self.normal_args + [option], option)

    def test_snapshot_version(self):
        """Координаты поддерживают версии SNAPSHOT."""
        arguments = self.normal_args.copy()
        arguments[1] = "org.example:my-lib:1.0-SNAPSHOT"
        self.assertEqual(parse_config(arguments).package, arguments[1])
