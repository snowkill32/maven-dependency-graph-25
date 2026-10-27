"""Проверки XML-формата POM и разделения типов объявлений."""

import unittest

from src.pom import Dependency, parse_pom


def make_pom(body: str = "", namespace: bool = True) -> bytes:
    """Создать минимальный POM для изолированного теста."""
    attribute = ' xmlns="http://maven.apache.org/POM/4.0.0"'
    if not namespace:
        attribute = ""
    return (
        f"<project{attribute}><modelVersion>4.0.0</modelVersion>"
        "<groupId>org.example</groupId><artifactId>demo</artifactId>"
        f"<version>1.0</version>{body}</project>"
    ).encode("utf-8")


class PomTests(unittest.TestCase):
    """Чтение только прямых зависимостей и необходимых метаданных."""

    def test_dependencies_with_and_without_namespace(self):
        """POM с namespace и без него дает одинаковый результат."""
        body = """
        <dependencies><dependency>
          <groupId> org.sample </groupId><artifactId>library</artifactId>
          <version>2.1</version><scope>test</scope><optional>true</optional>
          <type>test-jar</type><classifier>tests</classifier>
        </dependency></dependencies>
        """
        for namespace in (True, False):
            with self.subTest(namespace=namespace):
                pom = parse_pom(make_pom(body, namespace))
                self.assertEqual(pom.dependencies, [Dependency(
                    "org.sample", "library", "2.1", "test", "test-jar",
                    "tests", "true",
                )])

    def test_plugin_and_management_are_not_direct_dependencies(self):
        """Плагины, профили и dependencyManagement не попадают в список."""
        body = """
        <dependencyManagement><dependencies><dependency>
          <groupId>g</groupId><artifactId>managed</artifactId>
          <version>1</version>
        </dependency></dependencies></dependencyManagement>
        <build><plugins><plugin><dependencies><dependency>
          <groupId>g</groupId><artifactId>plugin</artifactId>
        </dependency></dependencies></plugin></plugins></build>
        <profiles><profile><dependencies><dependency>
          <groupId>g</groupId><artifactId>profile</artifactId>
        </dependency></dependencies></profile></profiles>
        """
        pom = parse_pom(make_pom(body))
        self.assertEqual(pom.dependencies, [])
        self.assertEqual(pom.managed[0].artifact_id, "managed")

    def test_properties_and_parent(self):
        """Свойства и координаты родителя сохраняются для обработки."""
        body = """
        <parent><groupId>g</groupId><artifactId>parent</artifactId>
          <version>2</version></parent>
        <properties><lib.version>3</lib.version><empty/></properties>
        """
        pom = parse_pom(make_pom(body))
        self.assertEqual(pom.parent,
                         {"groupId": "g", "artifactId": "parent",
                          "version": "2"})
        self.assertEqual(pom.properties, {"lib.version": "3", "empty": ""})

    def test_no_dependencies(self):
        """Отсутствующий раздел зависимостей означает пустой список."""
        self.assertEqual(parse_pom(make_pom()).dependencies, [])

    def test_invalid_documents(self):
        """Ошибки XML, корня и версии модели объясняются пользователю."""
        cases = [(b"<project>", "XML"), (b"<html/>", "project"),
                 (b"<project><modelVersion>5</modelVersion></project>",
                  "modelVersion")]
        for content, message in cases:
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, message):
                    parse_pom(content)
