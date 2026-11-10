"""Разрешение метаданных Maven без обхода зависимостей зависимостей."""

from collections.abc import Callable
from dataclasses import replace

from .config import validate_package
from .pom import Declaration, Dependency, Pom, parse_model
from .properties import (
    complete_dependency, expand, expand_declaration, merge_declaration,
    property_context,
)


MAX_POM_DEPTH = 32
IDENTITY_FIELDS = ("group_id", "artifact_id", "type", "classifier")


def coordinate_string(values: dict, properties: dict) -> str:
    """Получить проверенные координаты из трех полей с подстановками."""
    package = ":".join(expand(values.get(name, ""), properties)
                       for name in ("groupId", "artifactId", "version"))
    validate_package(package, False)
    return package


def declaration_key(item: Declaration, properties: dict) -> tuple:
    """Раскрыть только поля, различающие варианты одного артефакта."""
    identity = {name: expand(getattr(item, name), properties)
                for name in IDENTITY_FIELDS}
    return replace(item, **identity).key


def merge_declarations(base: list, own: list, properties: dict) -> list:
    """Слить объявления по ключу, сохранив сырые свойства для наследников."""
    result = {}
    for item in [*base, *own]:
        key = declaration_key(item, properties)
        previous = result.get(key, Declaration())
        result[key] = merge_declaration(previous, item)
    return list(result.values())


def inherit_pom(parent: Pom, child: Pom) -> Pom:
    """Унаследовать группу, версию, свойства и объявления зависимостей."""
    coordinates = dict(child.coordinates)
    for name in ("groupId", "version"):
        coordinates[name] = coordinates.get(name) or parent.coordinates.get(
            name, "",
        )
    result = Pom(
        coordinates=coordinates, parent=child.parent,
        properties={**parent.properties, **child.properties},
    )
    properties = property_context(result)
    result.coordinates = {name: expand(value, properties)
                          for name, value in coordinates.items()}
    result.dependencies = merge_declarations(
        parent.dependencies, child.dependencies, properties,
    )
    result.managed = merge_declarations(
        parent.managed, child.managed, properties,
    )
    return result


class PomResolver:
    """Собрать метаданные проекта; повторные POM хранить в памяти."""

    def __init__(self, load: Callable[[str], bytes]):
        """Принять загрузчик, подготовить кэш и цепочку разрешения POM."""
        self.load = load
        self.cache: dict[str, Pom] = {}
        self.loading: list[str] = []

    def model(self, package: str) -> Pom:
        """Загрузить POM, родителей и BOM с проверкой циклов метаданных."""
        validate_package(package, False)
        if package in self.cache:
            return self.cache[package]
        if package in self.loading:
            raise ValueError(f"цикл родительских POM или BOM: {package}")
        if len(self.loading) >= MAX_POM_DEPTH:
            raise ValueError("слишком длинная цепочка родительских POM или BOM")
        self.loading.append(package)
        try:
            child = parse_model(self.load(package))
            parent = Pom()
            if child.parent:
                name = coordinate_string(child.parent, property_context(child))
                parent = self.model(name)
            model = inherit_pom(parent, child)
            actual = coordinate_string(
                model.coordinates, property_context(model),
            )
            if actual != package:
                raise ValueError(f"вместо {package} получен POM {actual}")
            model.managed = self.import_management(model)
            self.cache[package] = model
            return model
        except ValueError as error:
            raise ValueError(f"{package}: {error}") from error
        finally:
            self.loading.pop()

    def import_management(self, model: Pom) -> list[Declaration]:
        """Добавить версии из BOM, сохранив приоритет явных объявлений."""
        properties = property_context(model)
        result, imports = {}, []
        for item in model.managed:
            if expand(item.scope, properties) == "import":
                imports.append(expand_declaration(item, properties))
            else:
                result[declaration_key(item, properties)] = item
        for item in imports:
            if item.type != "pom":
                raise ValueError("BOM со scope=import должен иметь type=pom")
            name = f"{item.group_id}:{item.artifact_id}:{item.version}"
            bom = self.model(name)
            for raw in bom.managed:
                resolved = expand_declaration(raw, property_context(bom))
                result.setdefault(resolved.key, resolved)
        return list(result.values())

    def direct_dependencies(self, package: str) -> list[Dependency]:
        """Вернуть все прямые зависимости с разрешенными версиями и полями."""
        model = self.model(package)
        properties = property_context(model)
        management = {declaration_key(item, properties): item
                      for item in model.managed}
        result = []
        for raw in model.dependencies:
            item = expand_declaration(raw, properties)
            managed = management.get(item.key, Declaration())
            result.append(complete_dependency(
                item, expand_declaration(managed, properties),
            ))
        return result
