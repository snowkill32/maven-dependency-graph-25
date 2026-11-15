"""Проверки тестового репозитория, ошибочных описаний и примеров графов."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.local_repository import get_test_graph, load_test_repository


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class LocalRepositoryTests(unittest.TestCase):
    """Тестовый граф проверяется целиком, обходится только достижимая часть."""

    def setUp(self):
        """Подготовить отдельную папку для JSON с разными ошибками."""
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "repository.json"

    def write_graph(self, graph):
        """Сохранить описание репозитория как JSON в UTF-8."""
        self.path.write_text(json.dumps(graph), encoding="utf-8")
        return str(self.path)

    def test_example_with_shared_dependency(self):
        """Общий D сохраняется в двух списках, недостижимый Z не обходится."""
        result = get_test_graph("A", str(EXAMPLES / "repository.json"))
        self.assertEqual(list(result), ["A", "B", "C", "D", "E"])
        self.assertEqual(result["B"], ["D"])
        self.assertEqual(result["C"], ["D", "E"])
        self.assertNotIn("Z", result)

    def test_cycle_examples(self):
        """Цикл из трех вершин и петля остаются конечными графами."""
        cases = [("cycle.json", {"A": ["B"], "B": ["C"], "C": ["A"]}),
                 ("self_cycle.json", {"A": ["A"]})]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(get_test_graph("A", str(EXAMPLES / filename)),
                                 expected)

    def test_isolated_root(self):
        """Несвязанные компоненты репозитория не входят в граф корня."""
        result = get_test_graph("A", str(EXAMPLES / "isolated.json"))
        self.assertEqual(result, {"A": []})

    def test_missing_root(self):
        """Пользователь получает сообщение, если выбранного пакета нет."""
        for graph in ({}, {"B": []}):
            with self.subTest(graph=graph):
                self.write_graph(graph)
                with self.assertRaisesRegex(ValueError, "пакет A отсутствует"):
                    get_test_graph("A", str(self.path))

    def test_invalid_json(self):
        """Поврежденный JSON не превращается в пустой граф."""
        self.path.write_text('{"A": [}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "тестовый JSON"):
            load_test_repository(str(self.path))

    def test_duplicate_declaration(self):
        """Повтор ключа A не должен незаметно затирать его зависимости."""
        self.path.write_text('{"A": [], "A": ["A"]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "повторное объявление"):
            load_test_repository(str(self.path))

    def test_wrong_root_type(self):
        """Корнем JSON должен быть объект, а не массив или скаляр."""
        for graph in ([], None, "A", 1):
            with self.subTest(graph=graph):
                self.write_graph(graph)
                with self.assertRaisesRegex(ValueError, "объектом JSON"):
                    load_test_repository(str(self.path))

    def test_invalid_package_names(self):
        """Имена узлов должны быть одной большой латинской буквой."""
        for name in ("a", "AA", "А", "1", ""):
            with self.subTest(name=name):
                self.write_graph({name: []})
                with self.assertRaisesRegex(ValueError, "буквой A-Z"):
                    load_test_repository(str(self.path))

    def test_dependencies_must_be_list(self):
        """Строка, объект и null вместо списка зависимостей отклоняются."""
        for neighbors in ("B", {}, None):
            with self.subTest(neighbors=neighbors):
                self.write_graph({"A": neighbors})
                with self.assertRaisesRegex(ValueError, "списком"):
                    load_test_repository(str(self.path))

    def test_invalid_neighbor_names(self):
        """Числа, вложенные объекты и неверные строки не являются узлами."""
        for neighbor in (1, None, {}, ["B"], "b", "BC", "Б"):
            with self.subTest(neighbor=neighbor):
                self.write_graph({"A": [neighbor]})
                with self.assertRaisesRegex(ValueError, "должно быть A-Z"):
                    load_test_repository(str(self.path))

    def test_dangling_reference(self):
        """Каждый упомянутый сосед должен иметь объявление в репозитории."""
        self.write_graph({"A": ["B"]})
        with self.assertRaisesRegex(ValueError, "не объявлен пакет B"):
            load_test_repository(str(self.path))

    def test_utf8_bom(self):
        """UTF-8 с BOM поддерживается при сохранении JSON в Windows."""
        self.path.write_text('{"A": []}', encoding="utf-8-sig")
        self.assertEqual(load_test_repository(str(self.path)), {"A": []})

    def test_read_errors(self):
        """Отказ чтения и неверная кодировка превращаются в ValueError."""
        with patch("src.local_repository.Path.read_text",
                   side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(ValueError, "тестовый JSON"):
                load_test_repository(str(self.path))
        self.path.write_bytes(b"\xff")
        with self.assertRaisesRegex(ValueError, "тестовый JSON"):
            load_test_repository(str(self.path))
