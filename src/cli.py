"""Опции командной строки, сообщения об ошибках и вывод конфигурации."""

import argparse
from collections.abc import Sequence

from .config import Config, validate_config


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер четырех пользовательских параметров."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25, этап 1: проверка и вывод конфигурации.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--package", required=True,
        help="координаты groupId:artifactId:version; в тестовом режиме A-Z",
    )
    parser.add_argument(
        "--repository", required=True,
        help="базовый HTTP(S) URL; с --test-mode путь к UTF-8 файлу",
    )
    parser.add_argument(
        "--test-mode", action="store_true",
        help="использовать локальный файл тестового репозитория",
    )
    parser.add_argument(
        "--ascii-tree", action="store_true",
        help="включить настройку ASCII-дерева (вывод появится на этапе 5)",
    )
    return parser


def parse_config(argv: Sequence[str] | None = None) -> Config:
    """Прочитать аргументы; при ошибке вывести справку и завершиться с 2."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    config = Config(**vars(arguments))
    try:
        validate_config(config)
    except ValueError as error:
        parser.error(str(error))
    return config


def format_config(config: Config) -> str:
    """Вернуть все настройки в формате ключ=значение."""
    return "\n".join(
        (
            f"package={config.package}",
            f"repository={config.repository}",
            f"test_mode={str(config.test_mode).lower()}",
            f"ascii_tree={str(config.ascii_tree).lower()}",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Проверить конфигурацию и вывести ее; вернуть код успеха 0."""
    config = parse_config(argv)
    print(format_config(config))
    return 0
