"""Проверки подстановки свойств и заполнения полей прямых зависимостей."""

import unittest

from src.pom import Declaration, Dependency, Pom
from src.properties import complete_dependency, expand, property_context


class PropertyTests(unittest.TestCase):
    """Неизвестные значения не должны превращаться в неполный результат."""

    def test_nested_properties(self):
        """Составная версия может ссылаться на другое свойство."""
        properties = {"major": "2", "revision": "${major}.3"}
        self.assertEqual(expand("v${revision}-${major}", properties), "v2.3-2")

    def test_unknown_and_cyclic_properties(self):
        """Неизвестное имя и замкнутые ссылки дают явную ошибку."""
        cases = [({}, "неизвестное"), ({"x": "${x}"}, "циклическое"),
                 ({"x": "${y}", "y": "${x}"}, "циклическое")]
        for properties, message in cases:
            with self.subTest(properties=properties):
                with self.assertRaisesRegex(ValueError, message):
                    expand("${x}", properties)

    def test_project_and_parent_aliases(self):
        """Проект и родитель имеют разные координаты и псевдонимы."""
        model = Pom(
            coordinates={"groupId": "g", "artifactId": "app", "version": "2"},
            parent={"groupId": "p", "artifactId": "parent", "version": "1"},
        )
        properties = property_context(model)
        self.assertEqual(expand("${project.version}", properties), "2")
        self.assertEqual(expand("${pom.artifactId}", properties), "app")
        self.assertEqual(expand("${project.parent.groupId}", properties), "p")

    def test_missing_artifact_is_not_inherited(self):
        """Имя артефакта нельзя незаметно взять от родительского проекта."""
        model = Pom(parent={"groupId": "g", "artifactId": "parent",
                            "version": "1"})
        self.assertEqual(property_context(model)["project.artifactId"], "")

    def test_managed_fields_and_explicit_false(self):
        """Явные версия и false важнее управления, scope наследуется."""
        actual = complete_dependency(
            Declaration("g", "lib", "3", optional="false"),
            Declaration("g", "lib", "2", "runtime", "true"),
        )
        self.assertEqual(actual, Dependency("g", "lib", "3", "runtime"))

    def test_default_fields(self):
        """Версия приходит из управления, остальные поля из умолчаний."""
        actual = complete_dependency(
            Declaration("g", "lib"), Declaration("g", "lib", "2"),
        )
        self.assertEqual(actual, Dependency("g", "lib", "2"))

    def test_invalid_final_fields(self):
        """Пустая версия и неподдерживаемые scope/optional не маскируются."""
        cases = [(Declaration("g", "lib"), "version"),
                 (Declaration("g", "lib", "1", "bad"), "scope"),
                 (Declaration("g", "lib", "1", optional="yes"), "optional")]
        for item, message in cases:
            with self.subTest(item=item):
                with self.assertRaisesRegex(ValueError, message):
                    complete_dependency(item, Declaration())
