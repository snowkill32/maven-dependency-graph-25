"""Минимальный запуск приложения и справка командной строки."""

import argparse


def main() -> int:
    """Прочитать аргументы процесса и вывести сообщение о запуске."""
    parser = argparse.ArgumentParser(
        prog="maven-dependency-graph",
        description="Анализ зависимостей Maven. Вариант 25.",
        allow_abbrev=False,
    )
    parser.parse_args()
    print("Приложение анализа зависимостей Maven запущено.")
    return 0
