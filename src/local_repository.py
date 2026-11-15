"""Чтение тестового JSON-репозитория с именами пакетов A-Z."""

import json
from pathlib import Path

from .config import TEST_PACKAGE
from .graph import build_graph


def unique_packages(pairs: list) -> dict:
    """Не допустить незаметной замены повторного ключа при чтении JSON."""
    result = {}
    for package, dependencies in pairs:
        if package in result:
            raise ValueError(f"повторное объявление пакета {package}")
        result[package] = dependencies
    return result


def validate_node(package: str, dependencies: list, graph: dict) -> None:
    """Проверить имя вершины, список соседей и наличие их объявлений."""
    if not TEST_PACKAGE.fullmatch(package):
        raise ValueError(f"имя пакета должно быть буквой A-Z: {package}")
    if not isinstance(dependencies, list):
        raise ValueError(f"зависимости {package} должны быть списком")
    for dependency in dependencies:
        if not isinstance(dependency, str) or not TEST_PACKAGE.fullmatch(
            dependency,
        ):
            raise ValueError(f"у {package} имя зависимости должно быть A-Z")
        if dependency not in graph:
            raise ValueError(f"у {package} не объявлен пакет {dependency}")


def load_test_repository(repository: str) -> dict[str, list[str]]:
    """Прочитать UTF-8 JSON вида {пакет: [зависимости]} и проверить граф."""
    try:
        content = Path(repository).read_text(encoding="utf-8-sig")
        graph = json.loads(content, object_pairs_hook=unique_packages)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"не удалось прочитать тестовый JSON: {error}"
        ) from error
    if not isinstance(graph, dict):
        raise ValueError("тестовый репозиторий должен быть объектом JSON")
    for package, dependencies in graph.items():
        validate_node(package, dependencies, graph)
    return graph


def get_test_graph(package: str, repository: str) -> dict[str, list[str]]:
    """Построить достижимую часть тестового графа рекурсивным BFS."""
    graph = load_test_repository(repository)
    if package not in graph:
        raise ValueError(f"пакет {package} отсутствует в тестовом репозитории")
    return build_graph(package, graph.__getitem__)
