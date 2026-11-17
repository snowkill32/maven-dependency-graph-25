"""Проверки порядка загрузки на DAG, циклах и длинных цепочках."""

import unittest

from src.order import dependency_order, format_load_order


class OrderTests(unittest.TestCase):
    """Зависимость должна появляться раньше каждого использующего пакета."""

    def test_shared_dependencies(self):
        """Общий узел учитывается один раз, исходный граф не меняется."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"],
                 "D": [], "E": []}
        before = {name: list(children) for name, children in graph.items()}
        order = dependency_order("A", graph)
        self.assertEqual(order, ["D", "B", "E", "C", "A"])
        for package, children in graph.items():
            for dependency in children:
                self.assertLess(order.index(dependency), order.index(package))
        self.assertEqual(graph, before)

    def test_leaf_and_unreachable_node(self):
        """Одиночный пакет выводится, чужая компонента не включается."""
        self.assertEqual(dependency_order("A", {"A": [], "Z": []}), ["A"])

    def test_cycles(self):
        """Петля и цикл из нескольких пакетов дают понятное объяснение."""
        cases = [({"A": ["A"]}, "A -> A"),
                 ({"A": ["B"], "B": ["C"], "C": ["A"]},
                  "A -> B -> C -> A")]
        for graph, path in cases:
            with self.subTest(graph=graph):
                with self.assertRaisesRegex(ValueError, path):
                    dependency_order("A", graph)

    def test_deep_graph(self):
        """Порядок глубокой цепочки не ограничен рекурсией Python."""
        names = [str(index) for index in range(1500)]
        graph = {name: [child] for name, child in zip(names, names[1:])}
        graph[names[-1]] = []
        self.assertEqual(dependency_order(names[0], graph), names[::-1])

    def test_format(self):
        """В текстовом выводе явно указано направление порядка."""
        self.assertEqual(format_load_order("A", {"A": ["B"], "B": []}),
                         "Порядок загрузки: B -> A")
