"""Проверки прямых зависимостей простого Maven POM."""

from pathlib import Path
import unittest

from src.pom import Dependency, parse_pom


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "simple.pom"


def pom_document(body: str = "", namespace: bool = True) -> bytes:
    """Создать минимальный POM с заданным содержимым для проверки."""
    attribute = ' xmlns="http://maven.apache.org/POM/4.0.0"'
    if not namespace:
        attribute = ""
    return (f"<project{attribute}><modelVersion>4.0.0</modelVersion>"
            f"{body}</project>").encode("utf-8")


def dependency_xml(version: str = "1", extra: str = "") -> str:
    """Создать раздел dependencies с одной зависимостью."""
    return ("<dependencies><dependency><groupId>g</groupId>"
            f"<artifactId>lib</artifactId><version>{version}</version>"
            f"{extra}</dependency></dependencies>")


class PomTests(unittest.TestCase):
    """Чтение POM, границы поиска и понятные ошибки исходных данных."""

    def test_example_dependencies(self):
        """Пример содержит обычную, тестовую и необязательную зависимости."""
        actual = parse_pom(EXAMPLE.read_bytes())
        self.assertEqual(actual, [
            Dependency("org.sample", "library", "2.1"),
            Dependency("junit", "junit", "4.13.2", "test"),
            Dependency("org.sample", "extension", "1.5", "runtime", True),
        ])
        self.assertEqual(actual[0].coordinates, "org.sample:library:2.1")

    def test_namespace_and_no_namespace(self):
        """Обычный namespace Maven и документ без namespace читаются."""
        for namespace in (True, False):
            with self.subTest(namespace=namespace):
                actual = parse_pom(pom_document(dependency_xml(), namespace))
                self.assertEqual(actual, [Dependency("g", "lib", "1")])

    def test_no_dependencies(self):
        """Отсутствующий или пустой раздел дает пустой список."""
        for body in ("", "<dependencies/>"):
            with self.subTest(body=body):
                self.assertEqual(parse_pom(pom_document(body)), [])

    def test_nested_sections_are_not_direct_dependencies(self):
        """Управление версиями, плагины и профили не попадают в результат."""
        body = """
        <dependencyManagement><dependencies><dependency>
          <groupId>g</groupId><artifactId>managed</artifactId>
          <version>1</version>
        </dependency></dependencies></dependencyManagement>
        <build><plugins><plugin><dependencies><dependency>
          <groupId>g</groupId><artifactId>plugin-lib</artifactId>
        </dependency></dependencies></plugin></plugins></build>
        <profiles><profile><dependencies><dependency>
          <groupId>g</groupId><artifactId>profile-lib</artifactId>
        </dependency></dependencies></profile></profiles>
        """
        self.assertEqual(parse_pom(pom_document(body)), [])

    def test_whitespace_around_values(self):
        """Пробельные отступы XML не становятся частью координат."""
        body = """
        <dependencies><dependency>
          <groupId> g </groupId><artifactId> lib </artifactId>
          <version> 1 </version><scope> test </scope>
          <optional> false </optional>
        </dependency></dependencies>
        """
        self.assertEqual(parse_pom(pom_document(body)),
                         [Dependency("g", "lib", "1", "test")])

    def test_missing_coordinate_fields(self):
        """Без любой части координат зависимость не считается разобранной."""
        for name in ("groupId", "artifactId", "version"):
            with self.subTest(name=name):
                fields = {"groupId": "g", "artifactId": "lib", "version": "1"}
                del fields[name]
                body = "<dependencies><dependency>"
                body += "".join(f"<{key}>{value}</{key}>"
                                for key, value in fields.items())
                body += "</dependency></dependencies>"
                with self.assertRaisesRegex(ValueError, name):
                    parse_pom(pom_document(body))

    def test_unresolved_property_is_reported(self):
        """Подстановка свойств еще не реализована: возвращается явная ошибка."""
        with self.assertRaisesRegex(ValueError, "свойства POM"):
            parse_pom(pom_document(dependency_xml("${lib.version}")))

    def test_invalid_scope_and_optional(self):
        """Неверные значения scope и optional не подменяются умолчаниями."""
        cases = [("<scope>unknown</scope>", "scope"),
                 ("<optional>yes</optional>", "optional")]
        for extra, message in cases:
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, message):
                    parse_pom(pom_document(dependency_xml(extra=extra)))

    def test_invalid_xml_root_and_model_version(self):
        """Поврежденный XML, HTML и чужая модель дают понятные ошибки."""
        cases = [(b"<project>", "XML POM"), (b"<html/>", "project"),
                 (b"<project><modelVersion>5</modelVersion></project>",
                  "modelVersion")]
        for content, message in cases:
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, message):
                    parse_pom(content)

    def test_invalid_xml_encoding(self):
        """Неизвестная или неподдерживаемая кодировка дает ValueError."""
        for encoding in ("unknown-charset", "UTF-32"):
            with self.subTest(encoding=encoding):
                content = (f'<?xml version="1.0" encoding="{encoding}"?>'
                           '<project/>').encode()
                with self.assertRaisesRegex(ValueError, "XML POM"):
                    parse_pom(content)
