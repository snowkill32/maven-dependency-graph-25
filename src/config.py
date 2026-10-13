"""Конфигурация приложения и проверка пользовательских параметров."""

from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
import re
from urllib.parse import SplitResult, urlsplit


MAVEN_PACKAGE = re.compile(
    r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*:"
    r"[A-Za-z0-9_][A-Za-z0-9_.-]*:"
    r"[A-Za-z0-9][A-Za-z0-9_.+-]*"
)
TEST_PACKAGE = re.compile(r"[A-Z]")
HOST_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
MIN_PORT = 1


@dataclass(frozen=True)
class Config:
    """Четыре настройки, полученные из командной строки."""

    package: str
    repository: str
    test_mode: bool = False
    ascii_tree: bool = False


def validate_package(package: str, test_mode: bool) -> None:
    """Проверить координаты Maven либо имя тестового пакета."""
    if test_mode:
        if not TEST_PACKAGE.fullmatch(package):
            raise ValueError(
                "--package: в тестовом режиме нужна буква A-Z, например A"
            )
        return
    if not MAVEN_PACKAGE.fullmatch(package):
        raise ValueError(
            "--package: ожидается groupId:artifactId:version, "
            "например org.example:demo:1.0"
        )


def validate_host(host: str) -> None:
    """Проверить синтаксис имени сервера или IPv6-адреса."""
    if ":" in host:
        ip_address(host)
    elif not HOST_NAME.fullmatch(host):
        raise ValueError("некорректное имя сервера")


def _validate_url_parts(url: SplitResult) -> None:
    """Проверить компоненты базового адреса репозитория."""
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("нужен абсолютный HTTP(S) URL с именем сервера")
    validate_host(url.hostname)
    if url.port is not None and url.port < MIN_PORT:
        raise ValueError("порт должен быть в диапазоне 1-65535")
    if url.username is not None or url.password is not None:
        raise ValueError("URL не должен содержать логин или пароль")
    if url.query or url.fragment:
        raise ValueError("нужен базовый URL без параметров и фрагмента")


def validate_url(repository: str) -> None:
    """Проверить базовый HTTP(S) URL без обращения к сети."""
    try:
        if any(char.isspace() for char in repository):
            raise ValueError("URL не должен содержать пробелы")
        _validate_url_parts(urlsplit(repository))
    except ValueError as error:
        raise ValueError(f"--repository: {error}") from error


def validate_test_file(repository: str) -> None:
    """Проверить, что тестовый репозиторий является читаемым UTF-8 файлом."""
    path = Path(repository)
    if not path.is_file():
        raise ValueError(
            "--repository: тестовый файл не найден или путь ведет к каталогу"
        )
    try:
        path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(
            "--repository: тестовый файл должен быть доступен для чтения "
            "и сохранен в UTF-8"
        ) from error


def validate_config(config: Config) -> None:
    """Проверить настройки с учетом выбранного режима репозитория."""
    validate_package(config.package, config.test_mode)
    if not config.repository.strip():
        raise ValueError("--repository: значение не должно быть пустым")
    if config.test_mode:
        validate_test_file(config.repository)
    else:
        validate_url(config.repository)
