"""Раскрытие свойств POM и применение управляемых значений зависимостей."""

from dataclasses import fields
import re

from .pom import Declaration, Dependency, Pom, SCOPES


PROPERTY = re.compile(r"\$\{([^{}]+)\}")
MAX_PROPERTY_DEPTH = 40
DEFAULTS = {"scope": "compile", "type": "jar", "optional": "false"}


def expand(value: str, properties: dict, trail: tuple = ()) -> str:
    """Раскрыть вложенные свойства; неизвестное имя или цикл дает ошибку."""
    def substitute(match):
        """Подставить одно свойство с проверкой цепочки ссылок."""
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
    """Добавить координаты проекта и родителя к пользовательским свойствам."""
    result = dict(pom.properties)
    for name in ("groupId", "artifactId", "version"):
        value = pom.coordinates.get(name, "")
        if name != "artifactId":
            value = value or pom.parent.get(name, "")
        for prefix in ("project.", "pom.", ""):
            result[prefix + name] = value
        if pom.parent:
            for prefix in ("project.parent.", "pom.parent.", "parent."):
                result[prefix + name] = pom.parent.get(name, "")
    return result


def expand_declaration(item: Declaration, properties: dict) -> Declaration:
    """Раскрыть свойства в каждом поле объявления зависимости."""
    return Declaration(**{
        field.name: expand(getattr(item, field.name), properties)
        for field in fields(Declaration)
    })


def merge_declaration(base: Declaration, own: Declaration) -> Declaration:
    """Явные поля дочернего объявления заменяют поля базового."""
    return Declaration(**{
        field.name: getattr(own, field.name) or getattr(base, field.name)
        for field in fields(Declaration)
    })


def complete_dependency(item: Declaration, managed: Declaration) -> Dependency:
    """Применить управление и умолчания, проверить обязательные поля."""
    result = merge_declaration(managed, item)
    values = {field.name: getattr(result, field.name)
              for field in fields(result)}
    for name, default in DEFAULTS.items():
        values[name] = values[name] or default
    for name in ("group_id", "artifact_id", "version"):
        if not values[name]:
            raise ValueError(f"в зависимости не задано поле {name}")
    if values["scope"] not in SCOPES:
        raise ValueError(f"неподдерживаемый scope: {values['scope']}")
    if values["optional"] not in {"true", "false"}:
        raise ValueError("optional зависимости должен быть true или false")
    values["optional"] = values["optional"] == "true"
    return Dependency(**values)
