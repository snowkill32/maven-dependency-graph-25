"""Опции командной строки и построение графа зависимостей третьего этапа."""

import argparse
from collections.abc import Sequence
import sys

from .config import Config, validate_config
from .graph import format_graph
from .local_repository import get_test_graph
from .order import format_load_order
from .repository import get_dependency_graph


def build_parser() -> argparse.ArgumentParser:
    """Описать две обязательные строковые настройки и два флага."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25: граф Maven и порядок загрузки зависимостей.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--package", required=True,
        help="groupId:artifactId:version; в тестовом режиме одна буква A-Z",
    )
    parser.add_argument(
        "--repository", required=True,
        help="HTTP(S) URL репозитория или путь к файлу с --test-mode",
    )
    parser.add_argument(
        "--test-mode", action="store_true",
        help="использовать локальный файл тестового репозитория",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--ascii-tree", action="store_true",
        help="использовать ASCII-символы вместо линий Unicode в схеме",
    )
    mode.add_argument(
        "--load-order", action="store_true",
        help="показать порядок загрузки: сначала зависимости, затем пакет",
    )
    return parser


def parse_config(argv: Sequence[str] | None = None) -> Config:
    """Прочитать и проверить настройки; ошибка дает stderr и код 2."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    config = Config(
        package=arguments.package,
        repository=arguments.repository,
        test_mode=arguments.test_mode,
        ascii_tree=arguments.ascii_tree,
        load_order=arguments.load_order,
    )
    try:
        validate_config(config)
    except ValueError as error:
        parser.error(str(error))
    return config


def main(argv: Sequence[str] | None = None) -> int:
    """Построить и вывести граф из Maven или тестового JSON-репозитория."""
    config = parse_config(argv)
    try:
        if config.test_mode:
            graph = get_test_graph(config.package, config.repository)
        else:
            graph = get_dependency_graph(config.package, config.repository)
        if config.load_order:
            output = format_load_order(config.package, graph)
        else:
            output = format_graph(config.package, graph, config.ascii_tree)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0
