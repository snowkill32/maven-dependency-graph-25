"""Проверки DOT, запуска Graphviz и открытия готового изображения."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.visualization import (
    dot_quote, format_dot, graphviz_executable, open_graph, render_graph,
)


class VisualizationTests(unittest.TestCase):
    """Связи не теряются, ошибки Graphviz становятся сообщениями CLI."""

    def setUp(self):
        """Подготовить отдельный каталог результатов с пробелами в имени."""
        directory = TemporaryDirectory(prefix="graph test ")
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name) / "result.png"

    def test_dot_preserves_cycle_shared_node_and_leaf(self):
        """DOT явно объявляет вершины и сохраняет каждое ребро графа."""
        graph = {"A": ["B", "C"], "B": ["C"], "C": ["A"], "D": []}
        dot = format_dot("A", graph)
        for node in graph:
            self.assertIn(f'"{node}"', dot)
        for source, children in graph.items():
            for target in children:
                self.assertIn(f'"{source}" -> "{target}";', dot)
        self.assertIn('"D";', dot)
        self.assertIn('fillcolor="lightblue"', dot)

    def test_dot_escapes_names(self):
        """Кавычки, слеши и переводы строк не меняют структуру DOT."""
        self.assertEqual(dot_quote('a"b\\c\nd'), '"a\\"b\\\\c\\nd"')

    def test_missing_graphviz(self):
        """При отсутствии dot сообщается о доступном ASCII-режиме."""
        with patch("src.visualization.shutil.which", return_value=None):
            with patch("src.visualization.Path.is_file", return_value=False):
                with self.assertRaisesRegex(ValueError, "--ascii-tree"):
                    graphviz_executable()

    def test_process_arguments_and_dot_file(self):
        """Пути с пробелами передаются отдельными аргументами без shell."""
        def run(arguments, **kwargs):
            """Имитировать создание файла внешней программой."""
            self.output.write_bytes(b"image")
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch("src.visualization.graphviz_executable", return_value="dot"):
            with patch("src.visualization.subprocess.run", side_effect=run) as p:
                result = render_graph("A", {"A": []}, str(self.output))
                self.assertEqual(result, self.output)
        self.assertEqual(p.call_args.args[0],
                         ["dot", "-Tpng", str(self.output.with_suffix(".dot")),
                          "-o", str(self.output)])
        self.assertIn('"A"', self.output.with_suffix(".dot").read_text())
        self.assertNotIn("shell", p.call_args.kwargs)

    def test_render_failures(self):
        """Ошибка процесса, тайм-аут и отсутствие результата не скрываются."""
        cases = [subprocess.CompletedProcess([], 1, "", "bad DOT"),
                 subprocess.TimeoutExpired("dot", 30),
                 FileNotFoundError("dot"),
                 subprocess.CompletedProcess([], 0, "", "")]
        for result in cases:
            with self.subTest(result=result):
                options = ({"side_effect": result} if isinstance(
                    result, Exception) else {"return_value": result})
                with patch("src.visualization.graphviz_executable",
                           return_value="dot"):
                    with patch("src.visualization.subprocess.run", **options):
                        with self.assertRaises(ValueError):
                            render_graph("A", {"A": []}, str(self.output))

    def test_invalid_output(self):
        """Неподдерживаемый формат не запускает внешнюю программу."""
        with self.assertRaisesRegex(ValueError, "--output"):
            render_graph("A", {"A": []}, "result.pdf")

    def test_open_windows_image(self):
        """Готовое изображение открывается через программу Windows."""
        with patch("src.visualization.sys.platform", "win32"):
            with patch("src.visualization.os.startfile", create=True) as start:
                open_graph(self.output)
        start.assert_called_once_with(str(self.output))

    def test_real_graphviz(self):
        """Установленный Graphviz строит настоящий PNG и SVG с циклом."""
        try:
            graphviz_executable()
        except ValueError:
            self.skipTest("Graphviz не установлен")
        graph = {"A": ["B"], "B": ["A"]}
        png = render_graph("A", graph, str(self.output))
        self.assertTrue(png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        svg = render_graph("A", graph, str(self.output.with_suffix(".svg")))
        self.assertIn("<svg", svg.read_text(encoding="utf-8"))
