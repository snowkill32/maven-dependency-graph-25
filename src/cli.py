"""Опции командной строки и вывод настроек первого этапа."""

import argparse
from collections.abc import Sequence

from .config import Config


def build_parser() -> argparse.ArgumentParser:
    """Описать две обязательные строковые настройки и два флага."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25, этап 1: настройки анализа зависимостей Maven.",
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
    """Получить настройки из argv или из аргументов запущенного процесса."""
    arguments = build_parser().parse_args(argv)
    return Config(
        package=arguments.package,
        repository=arguments.repository,
        test_mode=arguments.test_mode,
        ascii_tree=arguments.ascii_tree,
    )


def format_config(config: Config) -> str:
    """Сформировать четыре строки ключ=значение для первого этапа."""
    return "\n".join((
        f"package={config.package}",
        f"repository={config.repository}",
        f"test_mode={str(config.test_mode).lower()}",
        f"ascii_tree={str(config.ascii_tree).lower()}",
    ))


def main(argv: Sequence[str] | None = None) -> int:
    """Прочитать параметры и вывести конфигурацию приложения."""
    print(format_config(parse_config(argv)))
    return 0
