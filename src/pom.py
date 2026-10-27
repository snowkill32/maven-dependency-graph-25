"""Чтение описания Maven-пакета из XML без сторонних библиотек."""

from dataclasses import dataclass, field
from xml.etree import ElementTree


MAVEN_NAMESPACE = "http://maven.apache.org/POM/4.0.0"
COORDINATE_FIELDS = ("groupId", "artifactId", "version")
DEPENDENCY_FIELDS = {
    "group_id": "groupId",
    "artifact_id": "artifactId",
    "version": "version",
    "scope": "scope",
    "type": "type",
    "classifier": "classifier",
    "optional": "optional",
}


@dataclass(frozen=True)
class Dependency:
    """Поля зависимости; пустая строка означает отсутствие поля в POM."""

    group_id: str = ""
    artifact_id: str = ""
    version: str = ""
    scope: str = ""
    type: str = ""
    classifier: str = ""
    optional: str = ""

    @property
    def coordinates(self) -> str:
        """Вернуть координаты зависимости для вывода или загрузки POM."""
        return f"{self.group_id}:{self.artifact_id}:{self.version}"

    @property
    def key(self) -> tuple[str, str, str, str]:
        """Вернуть ключ Maven для слияния объявлений одной зависимости."""
        return (self.group_id, self.artifact_id, self.type or "jar",
                self.classifier)


@dataclass
class Pom:
    """Данные POM до подстановки свойств и наследования."""

    coordinates: dict[str, str] = field(default_factory=dict)
    parent: dict[str, str] = field(default_factory=dict)
    properties: dict[str, str] = field(default_factory=dict)
    dependencies: list[Dependency] = field(default_factory=list)
    managed: list[Dependency] = field(default_factory=list)


def element_text(element: ElementTree.Element, name: str) -> str:
    """Прочитать текст прямого дочернего элемента с любым namespace."""
    return element.findtext(f"{{*}}{name}", default="").strip()


def read_coordinates(element: ElementTree.Element) -> dict[str, str]:
    """Прочитать groupId, artifactId и version указанного элемента."""
    return {name: element_text(element, name) for name in COORDINATE_FIELDS}


def read_dependencies(root: ElementTree.Element, path: str) -> list:
    """Прочитать объявления из заданного раздела, исключая плагины."""
    result = []
    for element in root.findall(path):
        values = {name: element_text(element, tag)
                  for name, tag in DEPENDENCY_FIELDS.items()}
        result.append(Dependency(**values))
    return result


def parse_pom(content: bytes) -> Pom:
    """Разобрать POM 4.0.0; некорректный документ вызывает ValueError."""
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError(f"не удалось разобрать XML POM: {error}") from error
    if root.tag not in {"project", f"{{{MAVEN_NAMESPACE}}}project"}:
        raise ValueError("корневой элемент POM должен быть project")
    if element_text(root, "modelVersion") != "4.0.0":
        raise ValueError("поддерживается modelVersion 4.0.0")
    parent_element = root.find("{*}parent")
    parent = {}
    if parent_element is not None:
        parent = read_coordinates(parent_element)
    properties = {}
    for element in root.findall("{*}properties/*"):
        name = element.tag.rsplit("}", 1)[-1]
        properties[name] = (element.text or "").strip()
    return Pom(
        coordinates=read_coordinates(root), parent=parent,
        properties=properties,
        dependencies=read_dependencies(root, "{*}dependencies/{*}dependency"),
        managed=read_dependencies(
            root, "{*}dependencyManagement/{*}dependencies/{*}dependency",
        ),
    )
