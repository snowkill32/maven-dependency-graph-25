"""Проверки рекурсивного BFS, порядка уровней и сохранения связей графа."""

import unittest

from src.graph import build_graph, format_graph


class GraphTests(unittest.TestCase):
    """Циклы и общие зависимости не должны вызывать повторную загрузку."""

    def traverse(self, source, root="A"):
        """Вернуть граф и последовательность обращений к источнику."""
        calls = []

        def load(package):
            """Записать загрузку одной вершины и вернуть ее соседей."""
            calls.append(package)
            return source[package]

        return build_graph(root, load), calls

    def test_breadth_first_order(self):
        """Соседи корня читаются до более глубоких зависимостей."""
        source = {"A": ["B", "C"], "B": ["D", "E"], "C": ["F"],
                  "D": [], "E": [], "F": []}
        graph, calls = self.traverse(source)
        self.assertEqual(calls, ["A", "B", "C", "D", "E", "F"])
        self.assertEqual(list(graph), calls)

    def test_shared_dependency_and_duplicate_edges(self):
        """Общая вершина читается один раз, обе входящие связи сохраняются."""
        source = {"A": ["B", "B", "C"], "B": ["D"], "C": ["D"], "D": []}
        graph, calls = self.traverse(source)
        self.assertEqual(calls, ["A", "B", "C", "D"])
        self.assertEqual(graph["A"], ["B", "C"])
        self.assertEqual(graph["B"], ["D"])
        self.assertEqual(graph["C"], ["D"])

    def test_cycle_keeps_back_edge(self):
        """Цикл завершается, обратная связь не исчезает из результата."""
        graph, calls = self.traverse({"A": ["B"], "B": ["C"], "C": ["A"]})
        self.assertEqual(calls, ["A", "B", "C"])
        self.assertEqual(graph["C"], ["A"])

    def test_self_cycle(self):
        """Пакет, зависящий от себя, посещается один раз."""
        graph, calls = self.traverse({"A": ["A"]})
        self.assertEqual(graph, {"A": ["A"]})
        self.assertEqual(calls, ["A"])

    def test_unreachable_nodes_are_not_loaded(self):
        """В граф попадает только достижимая часть репозитория."""
        graph, calls = self.traverse({"A": [], "B": ["C"], "C": []})
        self.assertEqual(graph, {"A": []})
        self.assertEqual(calls, ["A"])

    def test_long_chain_does_not_exhaust_python_stack(self):
        """Цепочка глубже обычного лимита рекурсии обходится полностью."""
        nodes = [str(index) for index in range(1500)]
        source = {node: [neighbor] for node, neighbor in zip(nodes, nodes[1:])}
        source[nodes[-1]] = []
        graph, calls = self.traverse(source, nodes[0])
        self.assertEqual(calls, nodes)
        self.assertEqual(list(graph), nodes)
        self.assertEqual(graph[nodes[-1]], [])

    def test_loader_failure_is_not_hidden(self):
        """Ошибка чтения вершины передается вызывающему коду."""
        def load(package):
            """Смоделировать отсутствующее описание пакета."""
            raise ValueError(f"не найден {package}")

        with self.assertRaisesRegex(ValueError, "не найден A"):
            build_graph("A", load)

    def test_format_preserves_cycles_and_empty_lists(self):
        """Текст показывает порядок обхода, цикл и вершину без соседей."""
        self.assertEqual(format_graph("A", {"A": ["A", "B"], "B": []}),
                         "Граф зависимостей A:\n"
                         "A\n├── A [цикл]\n└── B (нет зависимостей)\n\n"
                         "Порядок обхода BFS: A, B")

    def test_shared_node_is_referenced_without_false_cycle(self):
        """Общая зависимость отличима от цикла и не раскрывается повторно."""
        source = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        text = format_graph("A", source)
        self.assertEqual(text, "Граф зависимостей A:\nA\n"
                         "├── B\n│   └── D (нет зависимостей)\n"
                         "└── C\n    └── D [уже показан выше]\n\n"
                         "Порядок обхода BFS: A, B, C, D")
        self.assertNotIn("[цикл]", text)

    def test_ascii_connectors(self):
        """ASCII-режим использует обычные символы для всех ветвей."""
        text = format_graph("A", {"A": ["B", "C"], "B": [], "C": []}, True)
        self.assertIn("+-- B (нет зависимостей)\n", text)
        self.assertIn("\\-- C (нет зависимостей)\n", text)
        self.assertNotIn("├", text)
        self.assertNotIn("└", text)

    def test_nested_cycle_is_marked_at_reference(self):
        """В цикле нескольких узлов метка ставится на возврате к предку."""
        text = format_graph("A", {"A": ["B"], "B": ["C"], "C": ["A"]})
        self.assertIn("        └── A [цикл]", text)
        self.assertEqual(text.count("[цикл]"), 1)

    def test_deep_tree_does_not_recurse(self):
        """Вывод глубокой цепочки не ограничен стеком вызовов Python."""
        nodes = [str(index) for index in range(1100)]
        graph = {node: [other] for node, other in zip(nodes, nodes[1:])}
        graph[nodes[-1]] = []
        text = format_graph(nodes[0], graph, True)
        self.assertIn("\\-- 1099 (нет зависимостей)", text)
        self.assertEqual(len(text.splitlines()), len(nodes) + 3)
