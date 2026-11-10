"""Чтение прямых зависимостей простого POM средствами стандартного XML API."""

from dataclasses import dataclass, field, fields
from xml.etree import ElementTree


MAVEN_NAMESPACE = "http://maven.apache.org/POM/4.0.0"
SCOPES = {"compile", "provided", "runtime", "test", "system"}
COORDINATE_FIELDS = ("groupId", "artifactId", "version")
DECLARATION_FIELDS = {
    "group_id": "groupId", "artifact_id": "artifactId", "version": "version",
    "scope": "scope", "optional": "optional", "type": "type",
    "classifier": "classifier",
}


@dataclass(frozen=True)
class Dependency:
    """Координаты зависимости, область использования и необязательность."""

    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    optional: bool = False
    type: str = "jar"
    classifier: str = ""

    @property
    def coordinates(self) -> str:
        """Вернуть координаты в формате groupId:artifactId:version."""
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


@dataclass(frozen=True)
class Declaration:
    """Сырые поля зависимости до наследования, подстановок и умолчаний."""

    group_id: str = ""
    artifact_id: str = ""
    version: str = ""
    scope: str = ""
    optional: str = ""
    type: str = ""
    classifier: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        """Различить артефакт, его тип и classifier при слиянии объявлений."""
        return (self.group_id, self.artifact_id, self.type or "jar",
                self.classifier)


@dataclass
class Pom:
    """Поля проекта, свойства, прямые зависимости и управление версиями."""

    coordinates: dict[str, str] = field(default_factory=dict)
    parent: dict[str, str] = field(default_factory=dict)
    properties: dict[str, str] = field(default_factory=dict)
    dependencies: list[Declaration] = field(default_factory=list)
    managed: list[Declaration] = field(default_factory=list)


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
    return Dependency(
        group_id, artifact_id, version, scope, optional == "true",
        element_text(element, "type") or "jar",
        element_text(element, "classifier"),
    )


def parse_xml(content: bytes) -> ElementTree.Element:
    """Проверить XML, корневой элемент и версию модели POM."""
    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, LookupError, ValueError) as error:
        raise ValueError(f"не удалось прочитать XML POM: {error}") from error
    if root.tag not in {"project", f"{{{MAVEN_NAMESPACE}}}project"}:
        raise ValueError("корневой элемент POM должен быть project")
    if element_text(root, "modelVersion") != "4.0.0":
        raise ValueError("поддерживается modelVersion 4.0.0")
    return root


def parse_pom(content: bytes) -> list[Dependency]:
    """Прочитать простой POM с явно указанными координатами зависимостей."""
    root = parse_xml(content)
    elements = root.findall("{*}dependencies/{*}dependency")
    return [read_dependency(element) for element in elements]


def read_coordinates(element: ElementTree.Element) -> dict[str, str]:
    """Прочитать координаты проекта или ссылки на родителя."""
    return {name: element_text(element, name) for name in COORDINATE_FIELDS}


def read_declarations(root: ElementTree.Element, path: str) -> list:
    """Прочитать поля зависимостей, сохранив незаданные поля пустыми."""
    return [Declaration(**{
        item.name: element_text(element, DECLARATION_FIELDS[item.name])
        for item in fields(Declaration)
    }) for element in root.findall(path)]


def parse_model(content: bytes) -> Pom:
    """Получить модель для разрешения свойств, родительских POM и BOM."""
    root = parse_xml(content)
    parent = root.find("{*}parent")
    properties = {
        element.tag.rsplit("}", 1)[-1]: (element.text or "").strip()
        for element in root.findall("{*}properties/*")
    }
    return Pom(
        coordinates=read_coordinates(root),
        parent={} if parent is None else read_coordinates(parent),
        properties=properties,
        dependencies=read_declarations(
            root, "{*}dependencies/{*}dependency",
        ),
        managed=read_declarations(
            root, "{*}dependencyManagement/{*}dependencies/{*}dependency",
        ),
    )
