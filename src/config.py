"""Пользовательские настройки и проверки значений первого этапа."""

from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
import re
from urllib.parse import SplitResult, urlsplit


MAVEN_PACKAGE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_-]*"
    r"(?:\.[A-Za-z0-9_][A-Za-z0-9_-]*)*:"
    r"[A-Za-z0-9_][A-Za-z0-9_.-]*:"
    r"[A-Za-z0-9][A-Za-z0-9_.+-]*"
)
TEST_PACKAGE = re.compile(r"[A-Z]")
HOST_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?")
MIN_PORT = 1


@dataclass(frozen=True)
class Config:
    """Имя пакета, источник данных и два режима вывода и работы."""

    package: str
    repository: str
    test_mode: bool = False
    ascii_tree: bool = False


def validate_package(package: str, test_mode: bool) -> None:
    """Проверить координаты Maven или одну латинскую букву A-Z."""
    if test_mode:
        if not TEST_PACKAGE.fullmatch(package):
            raise ValueError("--package: в тестовом режиме нужна буква A-Z")
    elif not MAVEN_PACKAGE.fullmatch(package):
        raise ValueError(
            "--package: ожидается groupId:artifactId:version, "
            "например junit:junit:4.13.2"
        )


def validate_host(host: str) -> None:
    """Проверить ASCII-имя сервера или IPv6 без сетевых запросов."""
    if ":" in host:
        ip_address(host)
        return
    labels = host.removesuffix(".").split(".")
    if not all(HOST_LABEL.fullmatch(label) for label in labels):
        raise ValueError("некорректное имя сервера")


def validate_url_parts(url: SplitResult) -> None:
    """Проверить компоненты базового HTTP(S)-адреса репозитория."""
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("нужен абсолютный HTTP(S) URL с именем сервера")
    validate_host(url.hostname)
    if url.port is not None and url.port < MIN_PORT:
        raise ValueError("порт должен быть в диапазоне 1-65535")
    if url.username is not None or url.password is not None:
        raise ValueError("логин и пароль в URL не поддерживаются")
    if url.query or url.fragment:
        raise ValueError("нужен базовый URL без query-параметров и фрагмента")


def validate_url(repository: str) -> None:
    """Проверить синтаксис URL и добавить имя опции к сообщению об ошибке."""
    try:
        if any(character.isspace() for character in repository):
            raise ValueError("URL не должен содержать пробелы")
        validate_url_parts(urlsplit(repository))
    except ValueError as error:
        raise ValueError(f"--repository: {error}") from error


def validate_test_file(repository: str) -> None:
    """Проверить наличие обычного читаемого файла с текстом UTF-8."""
    path = Path(repository)
    if not path.is_file():
        raise ValueError("--repository: нужен существующий файл, не каталог")
    try:
        path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(
            "--repository: файл должен быть доступен для чтения и иметь UTF-8"
        ) from error


def validate_config(config: Config) -> None:
    """Выбрать проверки пакета и репозитория по состоянию test_mode."""
    validate_package(config.package, config.test_mode)
    if not config.repository.strip():
        raise ValueError("--repository: значение не должно быть пустым")
    if config.test_mode:
        validate_test_file(config.repository)
    else:
        validate_url(config.repository)
