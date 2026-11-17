"""Проверка конфигурации, режимов вывода и ошибок параметров CLI."""

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
        self.image = self.directory / "graph.png"
        render = patch("src.cli.render_graph", return_value=self.image)
        self.render = render.start()
        self.addCleanup(render.stop)
        opener = patch("src.cli.open_graph")
        self.opener = opener.start()
        self.addCleanup(opener.stop)

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
        """Обычный запуск показывает граф, полученный от Maven-загрузчика."""
        output = StringIO()
        graph = {"junit:junit:4.13.2": ["g:lib:1"], "g:lib:1": []}
        with patch("src.cli.get_dependency_graph", return_value=graph) as load:
            with redirect_stdout(output):
                self.assertEqual(main(self.normal_args), 0)
        load.assert_called_once_with(
            "junit:junit:4.13.2", "https://repo1.maven.org/maven2/",
        )
        self.render.assert_called_once_with(
            "junit:junit:4.13.2", graph, "output/graph.png",
        )
        self.opener.assert_called_once_with(self.image)
        self.assertEqual(output.getvalue(),
                         f"Graphviz: {self.image.with_suffix('.dot')}\n"
                         f"Изображение: {self.image}\n")

    def test_normal_empty_dependencies(self):
        """Пакет без прямых зависимостей дает явное сообщение и успех."""
        output = StringIO()
        with patch("src.cli.get_dependency_graph",
                   return_value={"junit:junit:4.13.2": []}):
            with redirect_stdout(output):
                self.assertEqual(main(self.normal_args), 0)
        self.assertEqual(self.render.call_args.args[1],
                         {"junit:junit:4.13.2": []})
        self.assertIn("Изображение:", output.getvalue())

    def test_download_error_has_no_partial_output(self):
        """Ошибка получения POM дает stderr и код 1 без трассировки."""
        output, errors = StringIO(), StringIO()
        with patch("src.cli.get_dependency_graph",
                   side_effect=ValueError("POM не найден")):
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(main(self.normal_args), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "Ошибка: POM не найден\n")

    def test_test_mode_does_not_load_maven(self):
        """Тестовый режим обходит JSON и не обращается к Maven-репозиторию."""
        output = StringIO()
        with patch("src.cli.get_dependency_graph") as load:
            with redirect_stdout(output):
                self.assertEqual(main(self.test_args), 0)
        load.assert_not_called()
        self.assertEqual(self.render.call_args.args[1], {"A": []})
        self.assertIn("Изображение:", output.getvalue())

    def test_ascii_flag_selects_plain_connectors(self):
        """Флаг ASCII меняет линии схемы без изменения графа и порядка BFS."""
        output = StringIO()
        with patch("src.cli.get_dependency_graph",
                   return_value={"junit:junit:4.13.2": ["g:lib:1"],
                                 "g:lib:1": []}):
            with redirect_stdout(output):
                result = main(self.normal_args + ["--ascii-tree"])
        self.assertEqual(result, 0)
        self.assertIn("\\-- g:lib:1 (нет зависимостей)", output.getvalue())
        self.assertNotIn("└──", output.getvalue())
        self.render.assert_not_called()

    def test_bad_test_data_has_exit_one(self):
        """Ошибки JSON и отсутствие корня дают stderr без частичного графа."""
        for content in ('{"B": []}', '{"A": [}'):
            with self.subTest(content=content):
                self.repository.write_text(content, encoding="utf-8")
                output, errors = StringIO(), StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    self.assertEqual(main(self.test_args), 1)
                self.assertEqual(output.getvalue(), "")
                self.assertIn("Ошибка:", errors.getvalue())

    def test_default_flags_are_false(self):
        """Оба флага остаются выключенными без указания в командной строке."""
        config = parse_config(self.normal_args)
        self.assertFalse(config.test_mode)
        self.assertFalse(config.ascii_tree)
        self.assertFalse(config.no_open)
        self.assertEqual(config.output, "output/graph.png")

    def test_output_path_and_no_open(self):
        """Путь передается рендереру, окно можно отключить для сервера."""
        with redirect_stdout(StringIO()):
            result = main(self.test_args + ["--output", str(self.image),
                                            "--no-open"])
        self.assertEqual(result, 0)
        self.render.assert_called_once_with("A", {"A": []}, str(self.image))
        self.opener.assert_not_called()

    def test_invalid_output_format(self):
        """Ошибочная настройка формата имеет код 2 до загрузки данных."""
        for path in ("", "graph", "graph.pdf", "graph.dot"):
            with self.subTest(path=path):
                self.assert_error(self.normal_args + ["--output", path],
                                  "--output")

    def test_graphviz_error_is_reported(self):
        """Проблема визуализации дает код 1 без частичного stdout."""
        self.render.side_effect = ValueError("Graphviz не найден")
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            result = main(self.test_args)
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Graphviz не найден", errors.getvalue())

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
        for option in ("--test-mode", "--ascii-tree", "--no-open"):
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
                       "--ascii-tree", "--output", "--no-open"):
            self.assertIn(option, output.getvalue())
