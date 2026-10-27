"""Подстановка свойств POM и значений из dependencyManagement."""

from dataclasses import fields
import re

from .pom import Dependency, Pom


PROPERTY = re.compile(r"\$\{([^{}]+)\}")
MAX_PROPERTY_DEPTH = 40
DEPENDENCY_DEFAULTS = {"scope": "compile", "type": "jar", "optional": "false"}
SCOPES = {"compile", "provided", "runtime", "test", "system"}


def expand(value: str, properties: dict, trail: tuple = ()) -> str:
    """Подставить вложенные свойства, сообщив о неизвестном имени и цикле."""
    def substitute(match):
        """Раскрыть одно свойство, сохраняя цепочку для проверки цикла."""
        name = match.group(1)
        if name in trail or len(trail) >= MAX_PROPERTY_DEPTH:
            raise ValueError(
                f"циклическое или слишком вложенное свойство {name}"
            )
        if name not in properties:
            raise ValueError(f"неизвестное свойство POM: ${{{name}}}")
        return expand(properties[name], properties, (*trail, name))

    return PROPERTY.sub(substitute, value)


def property_context(pom: Pom) -> dict[str, str]:
    """Добавить к пользовательским свойствам координаты проекта и родителя."""
    result = dict(pom.properties)
    for name in ("groupId", "artifactId", "version"):
        value = pom.coordinates.get(name) or pom.parent.get(name, "")
        for prefix in ("project.", "pom.", ""):
            result[prefix + name] = value
        if pom.parent:
            for prefix in ("project.parent.", "pom.parent.", "parent."):
                result[prefix + name] = pom.parent.get(name, "")
    return result


def expand_dependency(dependency: Dependency, properties: dict) -> Dependency:
    """Раскрыть свойства во всех полях одного объявления зависимости."""
    return Dependency(**{
        item.name: expand(getattr(dependency, item.name), properties)
        for item in fields(Dependency)
    })


def merge_dependency(base: Dependency, own: Dependency) -> Dependency:
    """Объединить поля: явно заданное значение имеет приоритет."""
    return Dependency(**{
        item.name: getattr(own, item.name) or getattr(base, item.name)
        for item in fields(Dependency)
    })


def complete_dependency(
    dependency: Dependency, managed: Dependency,
) -> Dependency:
    """Применить управление и значения по умолчанию; проверить результат."""
    result = merge_dependency(managed, dependency)
    values = {item.name: getattr(result, item.name) for item in fields(result)}
    for name, default in DEPENDENCY_DEFAULTS.items():
        values[name] = values[name] or default
    result = Dependency(**values)
    if not all((result.group_id, result.artifact_id, result.version)):
        raise ValueError(
            f"не заданы groupId, artifactId или version: {result.coordinates}"
        )
    if result.scope not in SCOPES:
        raise ValueError(f"неподдерживаемый scope: {result.scope}")
    if result.optional not in {"true", "false"}:
        raise ValueError(
            f"optional должен быть true или false: {result.optional}"
        )
    return result
