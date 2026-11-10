"""Пользовательские настройки приложения."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Имя пакета, источник данных и два режима вывода и работы."""

    package: str
    repository: str
    test_mode: bool = False
    ascii_tree: bool = False
