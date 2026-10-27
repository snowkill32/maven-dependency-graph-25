"""Проверки адресов Maven layout и ошибок HTTP-загрузки."""

from http.client import IncompleteRead
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from src.repository import MAX_POM_BYTES, download_pom, pom_url


class RepositoryTests(unittest.TestCase):
    """Проверки транспорта без внешней сети."""

    def test_pom_path_keeps_repository_prefix(self):
        """groupId становится каталогами, исходный путь сохраняется."""
        expected = (
            "https://example.org/repository/releases/"
            "org/example/demo/1.0/demo-1.0.pom"
        )
        for base in ("https://example.org/repository/releases",
                     "https://example.org/repository/releases/"):
            with self.subTest(base=base):
                self.assertEqual(pom_url("org.example:demo:1.0", base),
                                 expected)

    def test_legacy_group_and_quoted_version(self):
        """Дефис в groupId допустим, плюс версии кодируется в URL."""
        actual = pom_url(
            "commons-io:commons-io:2.0+build", "https://example.org",
        )
        self.assertEqual(actual, "https://example.org/commons-io/commons-io/"
                         "2.0%2Bbuild/commons-io-2.0%2Bbuild.pom")

    def test_successful_download(self):
        """POM возвращается байтами с сохранением объявленной XML-кодировки."""
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"<project/>"
        with patch("src.repository.urlopen", return_value=response) as opened:
            actual = download_pom("g:app:1", "https://example.org")
        self.assertEqual(actual, b"<project/>")
        self.assertEqual(opened.call_args.args[0].full_url,
                         "https://example.org/g/app/1/app-1.pom")
        self.assertIn("timeout", opened.call_args.kwargs)

    def test_http_errors(self):
        """404 отличается от ошибки сервера и содержит координаты пакета."""
        for code, message in ((404, "не найден"), (500, "HTTP 500")):
            with self.subTest(code=code):
                error = HTTPError("https://example.org", code, "error",
                                  None, None)
                with patch("src.repository.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ValueError, message):
                        download_pom("g:app:1", "https://example.org")

    def test_connection_timeout_and_incomplete_response(self):
        """DNS, тайм-аут и оборванный ответ дают контролируемую ошибку."""
        errors = (URLError("DNS failed"), TimeoutError("timed out"),
                  IncompleteRead(b"partial", 20))
        for error in errors:
            with self.subTest(error=error):
                with patch("src.repository.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ValueError, "загрузить"):
                        download_pom("g:app:1", "https://example.org")

    def test_oversized_response(self):
        """Слишком большой ответ не передается XML-парсеру."""
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b"x" * (MAX_POM_BYTES + 1)
        )
        with patch("src.repository.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "размер"):
                download_pom("g:app:1", "https://example.org")
