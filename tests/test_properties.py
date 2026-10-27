"""Подстановка свойств, приоритет объявлений и значения по умолчанию."""

import unittest

from src.pom import Dependency, Pom
from src.properties import (
    complete_dependency, expand, expand_dependency, property_context,
)


class PropertyTests(unittest.TestCase):
    """Свойства должны раскрываться либо давать явную ошибку."""

    def test_nested_properties_and_multiple_substitutions(self):
        """Несколько свойств и вложенные ссылки раскрываются в строке."""
        properties = {"major": "2", "revision": "${major}.3"}
        self.assertEqual(expand("v${revision}-${major}", properties), "v2.3-2")

    def test_unknown_and_cyclic_properties(self):
        """Неизвестное имя и замкнутые ссылки не остаются в результате."""
        cases = [({}, "неизвестное"), ({"x": "${x}"}, "циклическое"),
                 ({"x": "${y}", "y": "${x}"}, "циклическое")]
        for properties, message in cases:
            with self.subTest(properties=properties):
                with self.assertRaisesRegex(ValueError, message):
                    expand("${x}", properties)

    def test_project_and_parent_aliases(self):
        """Координаты доступны через project.*, pom.* и parent.*."""
        pom = Pom(
            coordinates={"groupId": "g", "artifactId": "app", "version": "2"},
            parent={"groupId": "g", "artifactId": "parent", "version": "1"},
        )
        properties = property_context(pom)
        self.assertEqual(expand("${project.version}", properties), "2")
        self.assertEqual(expand("${pom.artifactId}", properties), "app")
        self.assertEqual(expand("${project.parent.version}", properties), "1")

    def test_property_in_dependency(self):
        """Свойства работают в координатах и scope зависимости."""
        dependency = Dependency("${group}", "lib", "${revision}", "${scope}")
        actual = expand_dependency(dependency, {
            "group": "g", "revision": "3", "scope": "test",
        })
        self.assertEqual(actual, Dependency("g", "lib", "3", "test"))

    def test_managed_version_and_defaults(self):
        """Отсутствующая версия берется из dependencyManagement."""
        actual = complete_dependency(
            Dependency("g", "lib"), Dependency("g", "lib", "2"),
        )
        self.assertEqual(actual,
                         Dependency("g", "lib", "2", "compile", "jar",
                                    "", "false"))

    def test_explicit_fields_override_management(self):
        """Явная версия и optional=false имеют приоритет над управлением."""
        actual = complete_dependency(
            Dependency("g", "lib", "3", optional="false"),
            Dependency("g", "lib", "2", "runtime", optional="true"),
        )
        self.assertEqual(actual.version, "3")
        self.assertEqual(actual.scope, "runtime")
        self.assertEqual(actual.optional, "false")

    def test_invalid_final_dependency(self):
        """Отсутствующая версия и неверные scope/optional не скрываются."""
        cases = [(Dependency("g", "lib"), "version"),
                 (Dependency("g", "lib", "1", "unknown"), "scope"),
                 (Dependency("g", "lib", "1", optional="yes"), "optional")]
        for dependency, message in cases:
            with self.subTest(dependency=dependency):
                with self.assertRaisesRegex(ValueError, message):
                    complete_dependency(dependency, Dependency())
