"""Чтение прямых зависимостей простого POM средствами стандартного XML API."""

from dataclasses import dataclass
from xml.etree import ElementTree


MAVEN_NAMESPACE = "http://maven.apache.org/POM/4.0.0"
SCOPES = {"compile", "provided", "runtime", "test", "system"}


@dataclass(frozen=True)
class Dependency:
    """Координаты зависимости, область использования и необязательность."""

    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    optional: bool = False

    @property
    def coordinates(self) -> str:
        """Вернуть координаты в формате groupId:artifactId:version."""
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


def element_text(element: ElementTree.Element, name: str) -> str:
    """Прочитать текст прямого дочернего элемента и убрать внешние пробелы."""
    return element.findtext(f"{{*}}{name}", default="").strip()


def required_text(element: ElementTree.Element, name: str) -> str:
    """Потребовать непустое поле с явно заданным значением без свойств."""
    value = element_text(element, name)
    if not value:
        raise ValueError(f"в зависимости не задано поле {name}")
    if "${" in value:
        raise ValueError(f"свойства POM в поле {name} пока не поддерживаются")
    return value


def read_dependency(element: ElementTree.Element) -> Dependency:
    """Прочитать объявление зависимости и проверить scope и optional."""
    group_id = required_text(element, "groupId")
    artifact_id = required_text(element, "artifactId")
    version = required_text(element, "version")
    scope = element_text(element, "scope") or "compile"
    optional = element_text(element, "optional") or "false"
    if scope not in SCOPES:
        raise ValueError(f"неподдерживаемый scope зависимости: {scope}")
    if optional not in {"true", "false"}:
        raise ValueError("optional зависимости должен быть true или false")
    return Dependency(group_id, artifact_id, version, scope, optional == "true")


def parse_pom(content: bytes) -> list[Dependency]:
    """Получить прямые зависимости POM 4.0.0; ошибки дают ValueError."""
    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, LookupError, ValueError) as error:
        raise ValueError(f"не удалось прочитать XML POM: {error}") from error
    if root.tag not in {"project", f"{{{MAVEN_NAMESPACE}}}project"}:
        raise ValueError("корневой элемент POM должен быть project")
    if element_text(root, "modelVersion") != "4.0.0":
        raise ValueError("поддерживается modelVersion 4.0.0")
    elements = root.findall("{*}dependencies/{*}dependency")
    return [read_dependency(element) for element in elements]
