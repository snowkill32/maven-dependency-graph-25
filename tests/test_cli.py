"""Проверка конфигурации и ошибок четырех параметров CLI."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.cli import main, parse_config


class ConfigTests(unittest.TestCase):
    """Успешные конфигурации и ошибки входных значений первого этапа."""

    def setUp(self):
        """Создать отдельный локальный файл для проверки тестового режима."""
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.repository = self.directory / "test repository.json"
        self.repository.write_text('{"A": []}', encoding="utf-8")
        self.normal_args = [
            "--package", "junit:junit:4.13.2",
            "--repository", "https://repo1.maven.org/maven2/",
        ]
        self.test_args = [
            "--package", "A", "--repository", str(self.repository),
            "--test-mode",
        ]

    def assert_error(self, arguments, message):
        """Проверить stderr, код 2 и отсутствие частичного результата."""
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as raised:
                main(arguments)
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(message, errors.getvalue())

    def test_normal_output(self):
        """Вывод содержит четыре параметра, оба флага по умолчанию false."""
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(self.normal_args), 0)
        self.assertEqual(output.getvalue(),
                         "package=junit:junit:4.13.2\n"
                         "repository=https://repo1.maven.org/maven2/\n"
                         "test_mode=false\nascii_tree=false\n")

    def test_test_mode_with_ascii_and_path_with_spaces(self):
        """Тестовый режим принимает существующий путь с пробелами."""
        config = parse_config(self.test_args + ["--ascii-tree"])
        self.assertEqual(config.package, "A")
        self.assertEqual(config.repository, str(self.repository))
        self.assertTrue(config.test_mode)
        self.assertTrue(config.ascii_tree)

    def test_ascii_flag_in_normal_mode(self):
        """ASCII-флаг может включаться независимо от тестового режима."""
        config = parse_config(self.normal_args + ["--ascii-tree"])
        self.assertTrue(config.ascii_tree)
        self.assertFalse(config.test_mode)

    def test_legacy_group_and_snapshot_version(self):
        """Имена с дефисом и синтаксис версии SNAPSHOT разрешены."""
        for package in ("commons-io:commons-io:2.16.1",
                        "org.example:my-lib:1.0-SNAPSHOT"):
            with self.subTest(package=package):
                arguments = self.normal_args.copy()
                arguments[1] = package
                self.assertEqual(parse_config(arguments).package, package)

    def test_missing_required_options(self):
        """Каждая из двух строковых опций обязательна."""
        cases = [([], "--package"),
                 (["--repository", "https://example.org"], "--package"),
                 (["--package", "g:app:1"], "--repository")]
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                self.assert_error(arguments, message)

    def test_missing_option_values(self):
        """После package и repository обязательно нужно значение."""
        for option in ("--package", "--repository"):
            with self.subTest(option=option):
                self.assert_error(self.normal_args + [option], option)

    def test_invalid_maven_package(self):
        """Пустые, неполные и содержащие пробелы координаты отклоняются."""
        for package in ("", "demo", "g:app", "g::1", "g:app:1:extra",
                        "g..x:app:1", "g:app:1 2", "../g:app:1"):
            with self.subTest(package=package):
                arguments = self.normal_args.copy()
                arguments[1] = package
                self.assert_error(arguments, "--package")

    def test_invalid_test_package(self):
        """Для тестового режима нужна одна большая латинская буква."""
        for package in ("", "a", "AB", "1", "А", "g:app:1"):
            with self.subTest(package=package):
                arguments = self.test_args.copy()
                arguments[1] = package
                self.assert_error(arguments, "A-Z")

    def test_valid_repository_urls(self):
        """Поддерживаются HTTP(S), порт и IPv6-адрес локального сервера."""
        urls = ("https://example.org/repository", "http://localhost:8080/",
                "http://127.0.0.1:8000/", "http://[::1]:8000/")
        for url in urls:
            with self.subTest(url=url):
                arguments = self.normal_args.copy()
                arguments[3] = url
                self.assertEqual(parse_config(arguments).repository, url)

    def test_invalid_repository_urls(self):
        """Ошибки схемы, хоста, порта и дополнительных частей URL видны."""
        urls = ("", " ", "repository.json", "ftp://example.org", "https://",
                "https://bad host", "https://a..b", "https://!!!",
                "https://example.org:0", "https://example.org:65536",
                "https://example.org:port", "https://[broken",
                "https://user:password@example.org",
                "https://example.org?x=1", "https://example.org#part")
        for url in urls:
            with self.subTest(url=url):
                arguments = self.normal_args.copy()
                arguments[3] = url
                self.assert_error(arguments, "--repository")

    def test_missing_test_file_or_directory(self):
        """Пустой путь, отсутствующий файл и каталог не принимаются."""
        paths = ("", " ", str(self.directory / "missing.json"),
                 str(self.directory), "https://example.org")
        for path in paths:
            with self.subTest(path=path):
                arguments = self.test_args.copy()
                arguments[3] = path
                self.assert_error(arguments, "--repository")

    def test_invalid_file_encoding(self):
        """Двоичные данные вместо текста UTF-8 вызывают понятную ошибку."""
        self.repository.write_bytes(b"\xff\xfe")
        self.assert_error(self.test_args, "UTF-8")

    def test_file_access_error(self):
        """Отказ чтения обрабатывается без трассировки исключения."""
        with patch("src.config.Path.read_text", side_effect=PermissionError):
            self.assert_error(self.test_args, "доступен для чтения")

    def test_boolean_flags_reject_values(self):
        """Флаги включаются присутствием и не принимают true или false."""
        for option in ("--test-mode", "--ascii-tree"):
            for value in ("true", "false"):
                with self.subTest(option=option, value=value):
                    self.assert_error(
                        self.normal_args + [f"{option}={value}"], option,
                    )

    def test_unknown_or_shortened_options(self):
        """Неизвестные опции и сокращенные имена явно отклоняются."""
        for option in ("--unknown", "--test", "--ascii"):
            with self.subTest(option=option):
                self.assert_error(self.normal_args + [option], option)

    def test_help_lists_all_options(self):
        """Справка описывает четыре параметра и завершается с кодом 0."""
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        for option in ("--package", "--repository", "--test-mode",
                       "--ascii-tree"):
            self.assertIn(option, output.getvalue())
