"""CLI анализа Maven и визуализации графа зависимостей."""

import argparse
from collections.abc import Sequence
import sys

from .config import Config, validate_config
from .graph import format_graph
from .local_repository import get_test_graph
from .repository import get_dependency_graph
from .visualization import open_graph, render_graph


def build_parser() -> argparse.ArgumentParser:
    """Описать две обязательные строковые настройки и два флага."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25: граф Maven, Graphviz и ASCII-дерево.",
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
    add_output_options(parser)
    return parser


def add_output_options(parser: argparse.ArgumentParser) -> None:
    """Описать режим ASCII, путь и открытие картинки."""
    parser.add_argument(
        "--ascii-tree", action="store_true",
        help="использовать ASCII-символы вместо линий Unicode в схеме",
    )
    parser.add_argument(
        "--output", default="output/graph.png",
        help="путь к изображению .png или .svg; рядом сохраняется .dot",
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="сохранить изображение, не открывая окно просмотра",
    )


def parse_config(argv: Sequence[str] | None = None) -> Config:
    """Прочитать и проверить настройки; ошибка дает stderr и код 2."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    config = Config(
        package=arguments.package,
        repository=arguments.repository,
        test_mode=arguments.test_mode,
        ascii_tree=arguments.ascii_tree,
        output=arguments.output,
        no_open=arguments.no_open,
    )
    try:
        validate_config(config)
    except ValueError as error:
        parser.error(str(error))
    return config


def display_result(config: Config, graph: dict) -> str:
    """Выбрать текстовый режим или сохранить и открыть изображение Graphviz."""
    if config.ascii_tree:
        return format_graph(config.package, graph, True)
    image = render_graph(config.package, graph, config.output)
    if not config.no_open:
        open_graph(image)
    return (f"Graphviz: {image.with_suffix('.dot')}\n"
            f"Изображение: {image}")


def main(argv: Sequence[str] | None = None) -> int:
    """Построить и вывести граф из Maven или тестового JSON-репозитория."""
    config = parse_config(argv)
    try:
        if config.test_mode:
            graph = get_test_graph(config.package, config.repository)
        else:
            graph = get_dependency_graph(config.package, config.repository)
        output = display_result(config, graph)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0
