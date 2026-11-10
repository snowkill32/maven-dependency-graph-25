"""Проверки адресов Maven и обработки ответов HTTP без внешней сети."""

from http.client import HTTPException
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.repository import (
    MAX_POM_BYTES, NETWORK_TIMEOUT_SECONDS, download_pom,
    get_direct_dependencies, pom_url,
)


REPOSITORY = "https://example.org/maven2"
PACKAGE = "org.example:app:1.0"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "simple.pom"


class RepositoryTests(unittest.TestCase):
    """Построение пути, успешный ответ и ошибки получения метаданных."""

    def test_maven_layout_and_trailing_slash(self):
        """Точки группы становятся каталогами, слеш базы не дублируется."""
        expected = REPOSITORY + "/org/example/app/1.0/app-1.0.pom"
        for base in (REPOSITORY, REPOSITORY + "/"):
            with self.subTest(base=base):
                self.assertEqual(pom_url(PACKAGE, base), expected)

    def test_version_characters_are_escaped(self):
        """Плюс в версии передается как часть пути URL, а не синтаксис."""
        self.assertEqual(
            pom_url("g:app:1.0+build", REPOSITORY),
            REPOSITORY + "/g/app/1.0%2Bbuild/app-1.0%2Bbuild.pom",
        )

    def test_invalid_inputs_do_not_open_network(self):
        """Неверные координаты и адрес обнаруживаются до запроса."""
        with patch("src.repository.urlopen") as open_url:
            for package, base in (("demo", REPOSITORY), (PACKAGE, "bad")):
                with self.subTest(package=package, base=base):
                    with self.assertRaises(ValueError):
                        download_pom(package, base)
            open_url.assert_not_called()

    def test_download_preserves_bytes_and_sets_timeout(self):
        """Кодировку разбирает XML-парсер, запрос ограничен по времени."""
        content = EXAMPLE.read_bytes()
        with patch("src.repository.urlopen", return_value=BytesIO(content)):
            self.assertEqual(download_pom(PACKAGE, REPOSITORY), content)
        with patch("src.repository.urlopen", return_value=BytesIO()) as load:
            download_pom(PACKAGE, REPOSITORY)
            request = load.call_args.args[0]
            self.assertEqual(request.full_url, pom_url(PACKAGE, REPOSITORY))
            self.assertEqual(load.call_args.kwargs,
                             {"timeout": NETWORK_TIMEOUT_SECONDS})

    def test_http_errors(self):
        """404 отличается от прочих HTTP-ошибок репозитория."""
        for code, message in ((404, "не найден"), (503, "HTTP 503")):
            with self.subTest(code=code):
                error = HTTPError(
                    "https://example.org", code, "error", {}, None,
                )
                with patch("src.repository.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ValueError, message):
                        download_pom(PACKAGE, REPOSITORY)

    def test_connection_and_read_errors(self):
        """Отказ соединения, тайм-аут и разрыв HTTP дают понятную ошибку."""
        errors = (URLError("offline"), TimeoutError("timeout"),
                  HTTPException("broken response"))
        for error in errors:
            with self.subTest(error=error):
                with patch("src.repository.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ValueError, "загрузить"):
                        download_pom(PACKAGE, REPOSITORY)

    def test_size_limit(self):
        """Слишком большой ответ не передается в XML-парсер."""
        content = b"x" * (MAX_POM_BYTES + 1)
        with patch("src.repository.urlopen", return_value=BytesIO(content)):
            with self.assertRaisesRegex(ValueError, "размер 2 МиБ"):
                download_pom(PACKAGE, REPOSITORY)

    def test_direct_dependencies_from_response(self):
        """Данные ответа проходят через настоящий разбор POM."""
        with patch("src.repository.urlopen",
                   return_value=BytesIO(EXAMPLE.read_bytes())):
            actual = get_direct_dependencies("org.example:demo:1.0", REPOSITORY)
        self.assertEqual([item.coordinates for item in actual], [
            "org.sample:library:2.1", "junit:junit:4.13.2",
            "org.sample:extension:1.5",
        ])

    def test_invalid_xml_from_response(self):
        """Успешный HTTP-ответ с испорченным XML все равно дает ошибку."""
        with patch("src.repository.urlopen", return_value=BytesIO(b"broken")):
            with self.assertRaisesRegex(ValueError, "XML POM"):
                get_direct_dependencies(PACKAGE, REPOSITORY)
