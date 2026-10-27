"""Родительские POM и BOM для получения списка прямых зависимостей."""

from collections.abc import Callable
from dataclasses import replace

from .config import validate_package
from .pom import Dependency, Pom, parse_pom
from .properties import (
    complete_dependency, expand, expand_dependency, merge_dependency,
    property_context,
)


MAX_POM_DEPTH = 32
IDENTITY_FIELDS = ("group_id", "artifact_id", "type", "classifier")


def coordinate_string(values: dict, properties: dict) -> str:
    """Получить проверенные координаты из полей с возможными свойствами."""
    package = ":".join(expand(values.get(name, ""), properties)
                       for name in ("groupId", "artifactId", "version"))
    validate_package(package, False)
    return package


def merge_declarations(base: list, own: list, properties: dict) -> list:
    """Объединить объявления по Maven-ключу, сохранив сырые версии."""
    result = {}
    for dependency in [*base, *own]:
        identity = {name: expand(getattr(dependency, name), properties)
                    for name in IDENTITY_FIELDS}
        dependency = replace(dependency, **identity)
        previous = result.get(dependency.key, Dependency())
        result[dependency.key] = merge_dependency(previous, dependency)
    return list(result.values())


def inherit_pom(parent: Pom, child: Pom) -> Pom:
    """Унаследовать свойства, зависимости и управление; дочернее важнее."""
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
    """Собрать POM из метаданных, не загружая зависимости зависимостей."""

    def __init__(self, load: Callable[[str], bytes]):
        """Принять функцию загрузки POM; хранить кэш только в памяти."""
        self.load = load
        self.cache: dict[str, Pom] = {}
        self.loading: list[str] = []

    def _model(self, package: str) -> Pom:
        """Прочитать POM, его родителей и BOM с проверкой циклов метаданных."""
        validate_package(package, False)
        if package in self.cache:
            return self.cache[package]
        if package in self.loading:
            raise ValueError(f"цикл родительских POM или BOM: {package}")
        if len(self.loading) >= MAX_POM_DEPTH:
            raise ValueError("слишком длинная цепочка родительских POM или BOM")
        self.loading.append(package)
        try:
            child = parse_pom(self.load(package))
            parent = Pom()
            if child.parent:
                name = coordinate_string(child.parent, property_context(child))
                parent = self._model(name)
            model = inherit_pom(parent, child)
            actual = coordinate_string(
                model.coordinates, property_context(model),
            )
            if actual != package:
                raise ValueError(f"вместо {package} получен POM {actual}")
            model.managed = self._import_management(model)
            self.cache[package] = model
            return model
        except ValueError as error:
            raise ValueError(f"{package}: {error}") from error
        finally:
            self.loading.pop()

    def _import_management(self, model: Pom) -> list[Dependency]:
        """Добавить управление из BOM; явные объявления имеют приоритет."""
        properties = property_context(model)
        result, imports = {}, []
        for dependency in model.managed:
            if expand(dependency.scope, properties) == "import":
                imports.append(expand_dependency(dependency, properties))
            else:
                result[dependency.key] = dependency
        for dependency in imports:
            if dependency.type != "pom":
                raise ValueError("BOM со scope=import должен иметь type=pom")
            bom = self._model(dependency.coordinates)
            bom_properties = property_context(bom)
            for item in bom.managed:
                resolved = expand_dependency(item, bom_properties)
                result.setdefault(resolved.key, resolved)
        return list(result.values())

    def direct_dependencies(self, package: str) -> list[Dependency]:
        """Вернуть прямые зависимости с версиями, scope, type и optional."""
        model = self._model(package)
        properties = property_context(model)
        management = {item.key: item for item in model.managed}
        result = []
        for raw in model.dependencies:
            dependency = expand_dependency(raw, properties)
            managed = management.get(dependency.key, Dependency())
            resolved = complete_dependency(
                dependency, expand_dependency(managed, properties),
            )
            result.append(resolved)
        return result
