"""Опции командной строки, сообщения об ошибках и вывод конфигурации."""

import argparse
from collections.abc import Sequence
import sys

from .config import Config, validate_config
from .pom import Dependency
from .repository import get_direct_dependencies


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер четырех пользовательских параметров."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Вариант 25, этап 2: прямые зависимости пакета Maven.",
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
        help="проверить локальную конфигурацию этапа 1 (граф будет на этапе 3)",
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


def format_dependencies(package: str, dependencies: list[Dependency]) -> str:
    """Сформировать плоский список всех прямых зависимостей пакета."""
    lines = [f"Прямые зависимости {package}:"]
    if not dependencies:
        lines.append("Прямых зависимостей нет.")
    for dependency in dependencies:
        details = [f"scope={dependency.scope}", f"type={dependency.type}"]
        if dependency.classifier:
            details.append(f"classifier={dependency.classifier}")
        details.append(f"optional={dependency.optional}")
        lines.append(f"- {dependency.coordinates} [{', '.join(details)}]")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Вывести зависимости либо конфигурацию тестового режима этапа 1."""
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
