# Анализ зависимостей Maven

Практическая работа №2, вариант 25. Реализованы этапы 1 и 2:
настройки командной строки, проверка ошибок, загрузка POM по HTTP(S)
и вывод всех прямых зависимостей указанного Maven-пакета.

Используется стандартная библиотека Python: `urllib` для HTTP,
`xml.etree.ElementTree` для XML, `argparse` для параметров.
Менеджеры пакетов и готовые библиотеки получения зависимостей не вызываются.
Родительские POM и импортированные BOM читаются как метаданные проекта;
POM самих зависимостей не загружаются. Обход графа из этапа 3 не реализован.

## Установка и запуск

Нужен Python 3.10 или новее. Сборка и установка дополнительных библиотек
не требуются. Все команды выполняются из корня проекта.

```shell
git clone --branch practice-2 https://github.com/snowkill32/maven-dependency-graph-25.git
cd maven-dependency-graph-25
python -m src --help
```

Пример получения зависимостей JUnit:

```shell
python -m src --package junit:junit:4.13.2 --repository https://repo1.maven.org/maven2/
```

```text
Прямые зависимости junit:junit:4.13.2:
  org.hamcrest:hamcrest-core:1.3 scope=compile optional=false type=jar classifier=-
  org.hamcrest:hamcrest-library:1.3 scope=test optional=false type=jar classifier=-
```

Версия является частью координат `groupId:artifactId:version`.
Выводятся также зависимости со scope `test` и optional `true`.
`classifier=-` означает, что classifier не указан.
Порядок строк отражает объявления после наследования, это не порядок загрузки.

Другие примеры:

```shell
python -m src --package com.google.guava:guava:33.3.1-jre --repository https://repo1.maven.org/maven2/
python -m src --package org.apache.commons:commons-lang3:3.17.0 --repository https://repo1.maven.org/maven2/
```

В Windows можно запускать тот же код через `run.bat`:

```powershell
.\run.bat --package junit:junit:4.13.2 --repository https://repo1.maven.org/maven2/
.\run.bat --help
```

Скрипт устанавливает UTF-8 для консоли, переходит в свой каталог,
передает аргументы Python и сохраняет код завершения.

## Настройки

| Опция | Назначение | По умолчанию |
| --- | --- | --- |
| `--package` | Координаты Maven; в тестовом режиме буква A-Z | Обязательна |
| `--repository` | Базовый HTTP(S) URL; в тестовом режиме путь к файлу | Обязательна |
| `--test-mode` | Проверка настроек локального тестового репозитория | `false` |
| `--ascii-tree` | Настройка будущего вывода ASCII-дерева на этапе 5 | `false` |

Флаг включается присутствием в команде: `--test-mode`, без `=true`.
Неизвестные и сокращенные опции отклоняются.
`--ascii-tree` сейчас не меняет вывод второго этапа.

Координаты содержат три непустые части без пробелов.
В группе разрешены буквы, цифры, `_`, дефисы и разделяющие сегменты точки.
Имя артефакта содержит буквы, цифры, `_`, точки и дефисы;
начинается с буквы, цифры или `_`. Версия начинается с буквы или цифры,
далее допускает буквы, цифры, точки, `_`, `+` и дефисы.

URL должен быть абсолютным HTTP(S)-адресом с ASCII-именем сервера
или IPv6-адресом. Допустимый порт: 1-65535. Пробелы, логин, пароль,
query-параметры и фрагмент не поддерживаются.
Синтаксическая проверка адреса не доказывает наличие пакета на сервере.
Для каждого HTTP-запроса задан тайм-аут 15 секунд и предел POM 2 МиБ.
Проверка HTTPS-сертификатов остается включенной.

### Тестовый режим

```shell
python -m src --package A --repository examples/repository.json --test-mode --ascii-tree
```

```text
package=A
repository=examples/repository.json
test_mode=true
ascii_tree=true
```

Имя пакета должно быть одной большой латинской буквой A-Z,
путь должен вести к существующему читаемому файлу UTF-8.
Пути с пробелами заключаются в кавычки. Относительный путь считается
от текущего рабочего каталога; `run.bat` предварительно меняет его на свой.

Здесь сохраняется поведение первого этапа: проверка и вывод настроек,
без сетевых запросов. Содержимое JSON еще не интерпретируется как граф,
наличие выбранного пакета в нем не проверяется. Это относится к этапу 3.

## Как получаются прямые зависимости

1. CLI читает и проверяет настройки.
2. Координаты переводятся в путь Maven Repository Layout:
   `group/path/artifact/version/artifact-version.pom`.
3. HTTP-клиент получает POM; XML-парсер читает модель 4.0.0.
4. При необходимости загружаются родительские POM и BOM.
5. Наследуются свойства и объявления, раскрываются `${...}`,
   применяются значения из `dependencyManagement` и умолчания.
6. CLI выводит каждую прямую зависимость с координатами, scope,
   optional, type и classifier. Для пустого списка выводится явное сообщение.

Поддерживаются пользовательские свойства, вложенные ссылки,
координаты `project.*`, `pom.*`, `parent.*` и `project.parent.*`.
Дочерние свойства и явно заданные поля имеют приоритет над родительскими.
Управление версиями не добавляет зависимость само по себе.
Импорт BOM требует `type=pom` и `scope=import`; при конфликте нескольких
BOM одного уровня используется первый импорт. Явное управление важнее BOM.
Тип и classifier входят в ключ, различающий варианты одного артефакта.

Если scope отсутствует, используется `compile`; для optional - `false`,
для type - `jar`. Списки плагинов и профилей не добавляются к зависимостям.
Кэш POM хранится в памяти на время анализа. Циклы метаданных и цепочки
родителей/BOM глубже 32 моделей дают ошибку. Это проверка метаданных,
а не реализация обхода графа транзитивных зависимостей.

Описание формата: [Maven Repository Layout](https://maven.apache.org/repositories/layout.html),
[Maven POM Reference](https://maven.apache.org/pom.html).

### Ограничения

Поддерживаются явно заданные версии опубликованных POM в Maven layout.
Не реализованы выбор latest, разрешение диапазонов версий и поиск
timestamped SNAPSHOT по `maven-metadata.xml`. Строка `1.0-SNAPSHOT`
синтаксически принимается, но используется только прямой путь к такому POM.
Не активируются профили, свойства окружения и системные свойства Maven.
Не обрабатываются relocation, локальный `relativePath` родителя,
дополнительные репозитории внутри POM и правила транзитивных exclusions.
Неизвестное используемое свойство или отсутствующая версия дает ошибку,
а не неполную строку зависимости. Это учебный анализатор, не полная
реализация Maven effective POM.

## Воспроизводимая демонстрация без интернета

В `tests/fixtures/maven2` находится маленький HTTP-репозиторий с POM.
В первом терминале из корня проекта:

```shell
python -m http.server 8000 --bind 127.0.0.1 --directory tests/fixtures/maven2
```

Во втором терминале из того же корня:

```shell
python -m src --package g:app:1 --repository http://127.0.0.1:8000/
```

```text
Прямые зависимости g:app:1:
  g:test-library:4 scope=test optional=false type=jar classifier=-
  g:library:2.5 scope=compile optional=false type=jar classifier=-
  g:extension:3.1 scope=runtime optional=true type=jar classifier=-
```

Тестовая зависимость приходит из родительского POM, версия `library`
берется из BOM, версия `extension` - из унаследованного свойства.
POM этих трех библиотек в репозитории отсутствуют и не запрашиваются.
Для остановки HTTP-сервера нажмите Ctrl+C в первом терминале.
Это HTTP-демонстрация второго этапа, флаг `--test-mode` здесь не нужен.

## Ошибки и коды завершения

| Код | Значение |
| --- | --- |
| `0` | Успешный результат или справка |
| `1` | Ошибка загрузки, XML или разрешения метаданных POM |
| `2` | Ошибка опций или пользовательских настроек |

Результат записывается в stdout, ошибка - в stderr. При ошибке данные
не выводятся частично; traceback пользователю не показывается.

Примеры ошибок настроек с кодом `2`:

```shell
python -m src --package demo --repository https://example.org
python -m src --package g:app:1 --repository not-a-url
python -m src --package A --repository examples/repository.json --test-mode=true
python -m src --package A --repository missing.json --test-mode
```

При запущенном локальном сервере следующие команды дают код `1`:

```shell
python -m src --package g:missing:1 --repository http://127.0.0.1:8000/
python -m src --package g:broken:1 --repository http://127.0.0.1:8000/
```

Причины: HTTP 404 и поврежденный XML. Отказ соединения, тайм-аут,
ошибка HTTPS-сертификата и слишком большой POM также дают код `1`.
В PowerShell код последней команды доступен через `$LASTEXITCODE`.

## Тесты

```shell
python -X utf8 -m unittest discover -s tests -v
```

69 тестов: 21 проверка CLI, 2 проверки точки входа,
10 проверок простого POM, 9 проверок HTTP-клиента,
7 проверок свойств, 17 проверок разрешения POM и 3 HTTP-интеграции.
Внешняя сеть и дополнительные библиотеки не нужны.

HTTP-интеграция запускает локальный сервер на свободном порту
и отдельный процесс Python, проверяет stdout, stderr, код завершения
и реальные запрошенные пути. Сервер закрывается после проверки.
Сетевые ошибки и ограничение размера проверяются подстановкой HTTP-ответа.
Наследование и BOM проверяются загрузчиком из словаря, включая циклы,
неизвестные свойства, приоритеты и отсутствие транзитивных запросов.

## Файлы и функции

| Файл | Назначение |
| --- | --- |
| `src/__main__.py` | Точка входа `python -m src` |
| `src/cli.py` | Параметры, запуск анализа и текстовый вывод |
| `src/config.py` | Контейнер настроек и проверки входных значений |
| `src/repository.py` | Адреса Maven и загрузка POM по HTTP(S) |
| `src/pom.py` | XML-парсер и модели данных |
| `src/properties.py` | Подстановка свойств и заполнение полей |
| `src/resolver.py` | Наследование и импорт управления из BOM |
| `examples/simple.pom` | Пример для отдельного простого парсера |
| `examples/repository.json` | Файл для проверки тестовых настроек |
| `tests/fixtures/maven2` | Небольшой HTTP-репозиторий для интеграции |
| `run.bat` | Запуск в Windows с сохранением кода завершения |

### CLI и настройки

- `build_parser()` описывает две обязательные опции и два флага.
- `parse_config(argv)` читает аргументы и превращает ошибки проверок в код `2`.
- `format_config(config)` формирует четыре строки настроек тестового режима.
- `format_dependencies(package, dependencies)` формирует список зависимостей.
- `main(argv)` выбирает режим, запускает анализ, обрабатывает ошибки данных.
- `Config` хранит `package`, `repository`, `test_mode`, `ascii_tree`;
  обычное изменение полей после создания запрещено через `frozen=True`.
- `validate_config(config)` выбирает проверки по режиму.
- `validate_package(package, test_mode)` проверяет координаты или букву A-Z.
- `validate_host(host)` проверяет ASCII-имя сервера либо IPv6.
- `validate_url_parts(url)` проверяет компоненты адреса.
- `validate_url(repository)` проверяет URL и добавляет имя опции к ошибке.
- `validate_test_file(repository)` проверяет наличие, чтение и UTF-8 файла.

### Загрузка и XML

- `pom_url(package, repository)` строит адрес POM по Maven layout.
- `download_pom(package, repository)` возвращает байты HTTP-ответа.
- `get_direct_dependencies(package, repository)` соединяет загрузчик с resolver.
- `Dependency` содержит разрешенные координаты, scope, optional, type, classifier;
  свойство `coordinates` возвращает `groupId:artifactId:version`.
- `Declaration` хранит сырые строковые поля; свойство `key` различает варианты.
- `Pom` хранит координаты, ссылку на родителя, свойства и два списка объявлений.
- `element_text(element, name)` читает текст прямого дочернего XML-элемента.
- `required_text(element, name)` требует явно заданное поле без `${...}`.
- `read_dependency(element)` читает одну зависимость простого POM.
- `parse_xml(content)` проверяет XML, корень project и modelVersion 4.0.0.
- `parse_pom(content)` отдельно разбирает простой POM с явными координатами.
- `read_coordinates(element)` читает поля координат проекта или родителя.
- `read_declarations(root, path)` читает сырые объявления из указанного раздела.
- `parse_model(content)` читает модель для последующего разрешения метаданных.

### Свойства и наследование

- `expand(value, properties, trail)` раскрывает свойства с защитой от циклов;
  вложенная `substitute(match)` обрабатывает одну ссылку.
- `property_context(pom)` объединяет свойства с псевдонимами координат.
- `expand_declaration(item, properties)` раскрывает поля одного объявления.
- `merge_declaration(base, own)` объединяет поля с приоритетом явных значений.
- `complete_dependency(item, managed)` применяет управление и умолчания,
  проверяет поля и возвращает `Dependency` с булевым optional.
- `coordinate_string(values, properties)` получает проверенную строку координат.
- `declaration_key(item, properties)` вычисляет ключ после подстановки свойств.
- `merge_declarations(base, own, properties)` объединяет объявления по ключу.
- `inherit_pom(parent, child)` наследует данные, сохраняя свойства для потомков.
- `PomResolver(load)` принимает функцию загрузки `str -> bytes`.
- `model(package)` получает модель с родителями и кэшем.
- `import_management(model)` разрешает импортированные BOM.
- `direct_dependencies(package)` получает окончательный список прямых зависимостей.

## История этапов

Первый этап с выводом конфигурации можно посмотреть на коммите `d417e19`.
Обычный запуск текущей ветки `practice-2` выполняет второй этап.
Для переключения версий удобно использовать отдельный обычный clone.
Убедитесь через `git status`, что нет несохраненных изменений:

```shell
git log --oneline
git checkout d417e19
python -m src --package junit:junit:4.13.2 --repository https://repo1.maven.org/maven2/
git checkout practice-2
```

`git log` показывает историю; `git checkout` меняет открытые исходники.
Переключение не запускает программу и не отправляет изменения на GitHub.
На конкретном коммите Git сообщает `detached HEAD`: это режим просмотра
версии вне ветки. Команда `git checkout practice-2` возвращает текущий код.
