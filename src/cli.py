"""Опции командной строки и вывод прямых зависимостей второго этапа."""

import argparse
from collections.abc import Sequence
import sys

from .config import Config, validate_config
from .pom import Dependency
from .repository import get_direct_dependencies


def build_parser() -> argparse.ArgumentParser:
    """Описать две обязательные строковые настройки и два флага."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25, этап 2: прямые зависимости Maven.",
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
    parser.add_argument(
        "--ascii-tree", action="store_true",
        help="включить настройку будущего вывода дерева (этап 5)",
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
    )
    try:
        validate_config(config)
    except ValueError as error:
        parser.error(str(error))
    return config


def format_config(config: Config) -> str:
    """Сформировать четыре строки ключ=значение для первого этапа."""
    return "\n".join((
        f"package={config.package}",
        f"repository={config.repository}",
        f"test_mode={str(config.test_mode).lower()}",
        f"ascii_tree={str(config.ascii_tree).lower()}",
    ))


def main(argv: Sequence[str] | None = None) -> int:
    """Вывести прямые зависимости; тестовый режим пока показывает настройки."""
    config = parse_config(argv)
    if config.test_mode:
        print(format_config(config))
        return 0
    try:
        dependencies = get_direct_dependencies(
            config.package, config.repository,
        )
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(format_dependencies(config.package, dependencies))
    return 0


def format_dependencies(package: str, dependencies: list[Dependency]) -> str:
    """Вывести каждую прямую зависимость с ее областью и вариантами."""
    lines = [f"Прямые зависимости {package}:"]
    for item in dependencies:
        lines.append(
            f"  {item.coordinates} scope={item.scope} "
            f"optional={str(item.optional).lower()} "
            f"type={item.type} classifier={item.classifier or '-'}"
        )
    if not dependencies:
        lines.append("  (нет прямых зависимостей)")
    return "\n".join(lines)
