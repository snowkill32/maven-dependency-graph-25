"""Проверка наследования и управления версиями без доступа к сети."""

import unittest

from src.resolver import PomResolver


def model_xml(artifact: str, body: str = "", version: str = "1") -> bytes:
    """Создать POM заданного артефакта для загрузчика из словаря."""
    return (
        '<project xmlns="http://maven.apache.org/POM/4.0.0">'
        '<modelVersion>4.0.0</modelVersion><groupId>g</groupId>'
        f'<artifactId>{artifact}</artifactId><version>{version}</version>'
        f'{body}</project>'
    ).encode()


def declaration(artifact: str, version: str = "", extra: str = "") -> str:
    """Создать объявление зависимости с необязательной версией."""
    return ("<dependency><groupId>g</groupId>"
            f"<artifactId>{artifact}</artifactId>"
            f"<version>{version}</version>{extra}</dependency>")


def parent_ref(artifact: str = "parent") -> str:
    """Создать ссылку на родительский POM."""
    return (f"<parent><groupId>g</groupId><artifactId>{artifact}</artifactId>"
            "<version>1</version></parent>")


def management(content: str) -> str:
    """Обернуть объявления в раздел dependencyManagement."""
    return ("<dependencyManagement><dependencies>" + content
            + "</dependencies></dependencyManagement>")


class ResolverTests(unittest.TestCase):
    """Проверки списка прямых зависимостей и вспомогательных POM."""

    def test_parent_properties_and_inherited_dependencies(self):
        """Дочернее свойство меняет версию унаследованной зависимости."""
        parent = model_xml("parent", """
            <properties><lib.version>2</lib.version></properties>
            <dependencies>""" + declaration("lib", "${lib.version}")
            + "</dependencies>")
        child = model_xml("app", parent_ref() + """
            <properties><lib.version>3</lib.version></properties>""")
        files = {"g:parent:1": parent, "g:app:1": child}
        resolver = PomResolver(files.__getitem__)
        self.assertEqual(resolver.direct_dependencies("g:app:1")[0].version,
                         "3")

    def test_parent_managed_version_and_child_override(self):
        """Управление наследуется, а явная дочерняя версия важнее."""
        files = {
            "g:parent:1": model_xml("parent", management(
                declaration("lib", "2") + declaration("other", "4"))),
            "g:app:1": model_xml("app", parent_ref() + "<dependencies>"
                                 + declaration("lib")
                                 + declaration("other", "5")
                                 + "</dependencies>"),
        }
        dependencies = PomResolver(files.__getitem__).direct_dependencies(
            "g:app:1",
        )
        self.assertEqual([item.version for item in dependencies], ["2", "5"])

    def test_inherited_group_and_version(self):
        """Проект может не повторять groupId и version родителя."""
        child = ("<project><modelVersion>4.0.0</modelVersion>"
                 "<artifactId>app</artifactId>" + parent_ref()
                 + "<dependencies>"
                 + declaration("lib", "${project.version}")
                 + "</dependencies></project>").encode()
        files = {"g:app:1": child, "g:parent:1": model_xml("parent")}
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual(result[0].coordinates, "g:lib:1")

    def test_bom_import_and_explicit_management(self):
        """BOM дает версии, локальное управление их переопределяет."""
        bom_ref = declaration(
            "bom", "1", "<type>pom</type><scope>import</scope>",
        )
        files = {
            "g:bom:1": model_xml("bom", management(
                declaration("lib", "2") + declaration("other", "3"))),
            "g:app:1": model_xml("app", management(
                bom_ref + declaration("other", "4")) + "<dependencies>"
                + declaration("lib") + declaration("other")
                + "</dependencies>"),
        }
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual([item.coordinates for item in result],
                         ["g:lib:2", "g:other:4"])

    def test_first_import_wins_and_bom_is_cached(self):
        """При конфликте BOM важнее первый импорт; повтор не грузится."""
        first = declaration(
            "bom", "1", "<type>pom</type><scope>import</scope>",
        )
        second = declaration(
            "bom2", "1", "<type>pom</type><scope>import</scope>",
        )
        files = {
            "g:bom:1": model_xml("bom", management(declaration("lib", "2"))),
            "g:bom2:1": model_xml("bom2", management(declaration("lib", "3"))),
            "g:app:1": model_xml("app", management(first + second)
                                 + "<dependencies>" + declaration("lib")
                                 + "</dependencies>"),
        }
        calls = []

        def load(package):
            """Записать реально запрошенные POM."""
            calls.append(package)
            return files[package]

        resolver = PomResolver(load)
        self.assertEqual(resolver.direct_dependencies("g:app:1")[0].version,
                         "2")
        resolver.direct_dependencies("g:app:1")
        self.assertEqual(calls.count("g:bom:1"), 1)

    def test_no_transitive_dependency_requests(self):
        """Зависимость выводится, но ее собственный POM не запрашивается."""
        files = {"g:app:1": model_xml("app", "<dependencies>"
                                    + declaration("unavailable", "1")
                                    + "</dependencies>")}
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual(result[0].coordinates, "g:unavailable:1")

    def test_cycle_in_parent_or_bom(self):
        """Цикл метаданных дает ошибку вместо зависания."""
        bodies = [parent_ref("app"), management(declaration(
            "app", "1", "<type>pom</type><scope>import</scope>",
        ))]
        for body in bodies:
            with self.subTest(body=body):
                files = {"g:app:1": model_xml("app", body)}
                with self.assertRaisesRegex(ValueError, "цикл"):
                    PomResolver(files.__getitem__).direct_dependencies(
                        "g:app:1",
                    )

    def test_incorrect_pom_coordinates(self):
        """Ответ сервера должен соответствовать запрошенному пакету."""
        files = {"g:app:1": model_xml("wrong")}
        with self.assertRaisesRegex(ValueError, "вместо"):
            PomResolver(files.__getitem__).direct_dependencies("g:app:1")

    def test_dependency_variants_are_not_merged(self):
        """type и classifier различают варианты одного артефакта."""
        body = "<dependencies>" + declaration("lib", "1")
        body += declaration("lib", "2", "<classifier>tests</classifier>")
        body += "</dependencies>"
        files = {"g:app:1": model_xml("app", body)}
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual([item.version for item in result], ["1", "2"])

    def test_imported_properties_use_bom_context(self):
        """Версия из BOM раскрывается по его свойствам, а не по дочерним."""
        bom = model_xml("bom", "<properties><v>2</v></properties>"
                        + management(declaration("lib", "${v}")))
        reference = declaration("bom", "1", "<type>pom</type>"
                                "<scope>import</scope>")
        app = model_xml("app", "<properties><v>3</v></properties>"
                        + management(reference) + "<dependencies>"
                        + declaration("lib") + "</dependencies>")
        files = {"g:app:1": app, "g:bom:1": bom}
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual(result[0].version, "2")

    def test_child_dependency_merges_parent_fields(self):
        """Явная версия заменяет родительскую, сохраняя унаследованный scope."""
        parent = model_xml("parent", "<dependencies>"
                           + declaration("lib", "1", "<scope>test</scope>")
                           + "</dependencies>")
        child = model_xml("app", parent_ref() + "<dependencies>"
                          + declaration("lib", "2") + "</dependencies>")
        files = {"g:app:1": child, "g:parent:1": parent}
        result = PomResolver(files.__getitem__).direct_dependencies("g:app:1")
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].version, result[0].scope), ("2", "test"))
