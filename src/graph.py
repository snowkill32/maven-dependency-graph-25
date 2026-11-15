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


def format_graph(root: str, graph: dict[str, list[str]]) -> str:
    """Показать порядок BFS и все ребра, включая обратные и общие связи."""
    lines = [f"Граф зависимостей {root}:",
             "Порядок обхода BFS: " + ", ".join(graph)]
    for package, dependencies in graph.items():
        neighbors = ", ".join(dependencies) or "(нет зависимостей)"
        lines.append(f"{package} -> {neighbors}")
    return "\n".join(lines)
