"""Построение достижимого графа зависимостей рекурсивным обходом в ширину."""

from collections.abc import Callable


RECURSIVE_LEVELS_PER_BATCH = 128


def build_graph(root: str, load: Callable[[str], list[str]]) -> dict:
    """Обойти граф уровнями; длинные цепочки разбить на блоки рекурсии."""
    graph = {}
    discovered = {root}

    def visit_level(frontier: list[str], remaining: int) -> list[str]:
        """Прочитать текущий уровень и рекурсивно перейти к следующему."""
        if not frontier or not remaining:
            return frontier
        next_level = []
        for package in frontier:
            dependencies = list(dict.fromkeys(load(package)))
            graph[package] = dependencies
            for dependency in dependencies:
                if dependency not in discovered:
                    discovered.add(dependency)
                    next_level.append(dependency)
        return visit_level(next_level, remaining - 1)

    frontier = [root]
    while frontier:
        frontier = visit_level(frontier, RECURSIVE_LEVELS_PER_BATCH)
    return graph


def reference_note(package: str, ancestors: frozenset, shown: set) -> str:
    """Различить возврат к предку и повторную ссылку на другую ветвь."""
    if package in ancestors:
        return " [цикл]"
    if package in shown:
        return " [уже показан выше]"
    return ""


def tree_lines(root: str, graph: dict, ascii_tree: bool = False) -> list[str]:
    """Развернуть связи в схему без повторного раскрытия узлов и рекурсии."""
    fork, last, vertical = (("+-- ", "\\-- ", "|   ") if ascii_tree
                            else ("├── ", "└── ", "│   "))
    lines, shown = [], set()
    stack = [(root, "", "", frozenset())]
    while stack:
        package, prefix, branch, ancestors = stack.pop()
        note = reference_note(package, ancestors, shown)
        if not graph[package] and not note:
            note = " (нет зависимостей)"
        lines.append(f"{prefix}{branch}{package}{note}")
        if package in shown:
            continue
        shown.add(package)
        child_prefix = prefix
        if branch:
            child_prefix += "    " if branch == last else vertical
        children = graph[package]
        for index in reversed(range(len(children))):
            connector = last if index == len(children) - 1 else fork
            stack.append((children[index], child_prefix, connector,
                          ancestors | {package}))
    return lines


def format_graph(root: str, graph: dict, ascii_tree: bool = False) -> str:
    """Показать схему связей и отдельно порядок BFS построения графа."""
    lines = [f"Граф зависимостей {root}:",
             *tree_lines(root, graph, ascii_tree), "",
             "Порядок обхода BFS: " + ", ".join(graph)]
    return "\n".join(lines)
