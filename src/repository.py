"""Получение POM из HTTP(S)-репозитория Maven средствами Python."""

from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import validate_package, validate_url
from .pom import Dependency
from .resolver import PomResolver


NETWORK_TIMEOUT_SECONDS = 15
MAX_POM_BYTES = 2 * 1024 * 1024
HTTP_NOT_FOUND = 404


def pom_url(package: str, repository: str) -> str:
    """Перевести group:artifact:version в адрес POM по Maven layout."""
    validate_package(package, False)
    validate_url(repository)
    group, artifact, version = package.split(":")
    group_path = "/".join(quote(part, safe="") for part in group.split("."))
    artifact_path = quote(artifact, safe="")
    version_path = quote(version, safe="")
    filename = f"{artifact_path}-{version_path}.pom"
    return (f"{repository.rstrip('/')}/{group_path}/{artifact_path}/"
            f"{version_path}/{filename}")


def download_pom(package: str, repository: str) -> bytes:
    """Загрузить POM с тайм-аутом и понятными сообщениями сетевых ошибок."""
    url = pom_url(package, repository)
    request = Request(url, headers={"User-Agent": "maven-dependency-graph/0.2"})
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            content = response.read(MAX_POM_BYTES + 1)
    except HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise ValueError(
                f"POM пакета {package} не найден: {url}"
            ) from error
        raise ValueError(
            f"репозиторий вернул HTTP {error.code}: {url}"
        ) from error
    except (URLError, OSError, HTTPException) as error:
        raise ValueError(f"не удалось загрузить {url}: {error}") from error
    if len(content) > MAX_POM_BYTES:
        raise ValueError(f"POM превышает допустимый размер 2 МиБ: {url}")
    return content


def get_direct_dependencies(package: str, repository: str) -> list[Dependency]:
    """Загрузить POM и вернуть все прямые зависимости без обхода графа."""
    resolver = PomResolver(lambda name: download_pom(name, repository))
    return resolver.direct_dependencies(package)
