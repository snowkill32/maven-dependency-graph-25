# Анализ зависимостей Maven

Практическая работа №2, вариант 25. Реализованы этапы 1-3 и 5:
параметры CLI, получение POM по HTTP(S), рекурсивный BFS с циклами,
тестовый JSON-репозиторий, Graphviz и ASCII-дерево.
Этап 4 не входит в итоговую версию.

Исходники используют только стандартную библиотеку Python. Maven и готовые
библиотеки получения зависимостей в программе не вызываются. Внешний Graphviz
используется только для превращения собственного DOT в изображение.
Maven использован отдельно при сравнении результатов.

## Установка и запуск

Нужен Python 3.10 или новее. Установка пакетов через pip не требуется.
Для изображений нужен [Graphviz](https://graphviz.org/download/).
При установке в Windows включите добавление Graphviz в PATH и заново
откройте терминал. Программа также ищет его в Program Files/Graphviz
и в LOCALAPPDATA/Programs/Graphviz. Проверка в терминале: `dot -V`.
Для ASCII-режима Graphviz не нужен.

```powershell
git clone --branch practice-2 https://github.com/snowkill32/maven-dependency-graph-25.git
cd maven-dependency-graph-25
python -m src --help
```

Команды выполняются из корня проекта, где находятся README.md и каталог src.
В Windows при наличии Python Launcher можно заменить `python` на `py -3`.
Сборка не требуется. `run.bat` включает UTF-8, переходит в каталог проекта,
передает аргументы Python и сохраняет код завершения.

## Изображение графа (этап 5)

Обычный запуск сохраняет `output/graph.dot` и `output/graph.png`,
затем открывает изображение программой просмотра ОС:

```powershell
$repo = "https://repo1.maven.org/maven2/"
python -m src --package junit:junit:4.13.2 --repository $repo
```

В терминале выводятся абсолютные пути к DOT и картинке. PNG/SVG содержит
все вершины и связи, включая циклы и общие зависимости; корень выделен цветом.
При отсутствии Graphviz выводится ошибка с предложением ASCII-режима.

Сохранить SVG по своему пути без открытия окна:

```powershell
python -m src --package junit:junit:4.13.2 --repository $repo --output output/junit.svg --no-open
```

Тот же запуск через Windows-скрипт:

```powershell
.\run.bat --package junit:junit:4.13.2 --repository $repo
```

## ASCII-дерево

```powershell
python -m src --package A --repository examples/repository.json --test-mode --ascii-tree
```

```text
Граф зависимостей A:
A
+-- B
|   \-- D (нет зависимостей)
\-- C
    +-- D [уже показан выше]
    \-- E (нет зависимостей)

Порядок обхода BFS: A, B, C, D, E
```

Под пакетом показаны прямые зависимости; вложенные ветви показывают
транзитивные. Общая зависимость раскрывается один раз, следующая ссылка
получает подпись `[уже показан выше]`. Возврат к предку отмечается `[цикл]`.
Схема оформляется отдельным стеком, порядок BFS выводится отдельной строкой.
Флаг ASCII меняет способ вывода; построение графа остается рекурсивным BFS.

## Настройки

| Опция | Назначение | По умолчанию |
| --- | --- | --- |
| `--package` | groupId:artifactId:version; с тестовым режимом буква A-Z | Обязательна |
| `--repository` | Базовый HTTP(S) URL; с тестовым режимом путь к JSON | Обязательна |
| `--test-mode` | Читать локальный JSON без сети | false |
| `--ascii-tree` | Печатать ASCII-дерево вместо изображения | false |
| `--output` | Путь изображения .png или .svg; рядом создается .dot | output/graph.png |
| `--no-open` | Сохранить изображение без окна просмотра | false |

Флаги включаются присутствием в команде, без `=true`.
`--output` и `--no-open` используются в режиме изображений.
Неизвестные и сокращенные параметры отклоняются.
Пути с пробелами заключаются в кавычки. Файлы результатов могут
перезаписываться при повторном запуске с тем же `--output`.

Координаты содержат три непустые части без пробелов. Версия является частью
имени вершины. Группа допускает буквы, цифры, подчеркивания и дефисы,
сегменты разделяются точками. Имя и версия допускают поддерживаемые Maven
буквы, цифры, точки и дефисы; точные проверки описаны в `src/config.py`.
URL должен иметь протокол HTTP(S), имя сервера и допустимый порт 1-65535.
Логин, пароль, query, fragment и пробельные символы в URL отклоняются.
Для HTTP задан тайм-аут 15 секунд и ограничение POM 2 МиБ.
Проверка HTTPS-сертификатов включена.

## Тестовый репозиторий и циклы

JSON содержит объект, где ключ - пакет A-Z, значение - список соседей:

```json
{"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": [], "E": [], "Z": []}
```

Каждый сосед должен иметь собственный ключ. Недостижимый из A пакет Z
не включается в результат. Повторы ключей, неправильные имена и типы,
ссылки на необъявленные вершины отклоняются. Принимается UTF-8 с BOM и без.

Примеры без интернета:

```powershell
python -m src --package A --repository examples/repository.json --test-mode
python -m src --package A --repository examples/cycle.json --test-mode --ascii-tree
python -m src --package A --repository examples/self_cycle.json --test-mode --ascii-tree
python -m src --package A --repository examples/isolated.json --test-mode --ascii-tree
```

`cycle.json`: A -> B -> C -> A. Вывод завершается, возврат к A отмечен циклом.
`self_cycle.json`: петля A -> A. `isolated.json`: выводится только одиночный A,
отдельная компонента B -> C не попадает в граф. Для изображения этих случаев
уберите `--ascii-tree`; при автоматической проверке добавьте `--no-open`.

## Три пакета и сравнение с Maven

```powershell
$repo = "https://repo1.maven.org/maven2/"
python -m src --package junit:junit:4.13.2 --repository $repo --output output/junit.png --no-open
python -m src --package org.hamcrest:hamcrest-library:1.3 --repository $repo --output output/library.png --no-open
python -m src --package org.hamcrest:hamcrest-core:1.3 --repository $repo --output output/core.png --no-open
```

Текстовые примеры DOT находятся в `examples/graphs`.
Сравнение выполнено 17.11.2026 с Maven 3.9.16 и dependency-plugin 3.8.1.
Maven сформировал собственные графы через `dependency:tree -DoutputType=dot`;
исходные проекты сравнения и его DOT сохранены в `examples/maven`.

| Пакет | Вершин у нас | Вершин Maven без служебного проекта | Результат |
| --- | --- | --- | --- |
| junit:junit:4.13.2 | 3 | 2 | У нас дополнительно hamcrest-library со scope=test |
| org.hamcrest:hamcrest-library:1.3 | 2 | 2 | Вершины и ребра совпадают |
| org.hamcrest:hamcrest-core:1.3 | 1 | 1 | Оба графа без зависимостей |

Maven сравнивался через внешний проект, зависящий от выбранного пакета.
Он исключает транзитивные test-зависимости; наш учебный обход сохраняет
все объявленные scope. Поэтому в JUnit есть дополнительная вершина и ребра.
Maven также добавляет корень demo:comparison:1 и scope/type в подписи.
При сравнении этот служебный корень исключен, подписи приведены к G:A:V.
Различия расположения узлов на рисунке не означают различий зависимостей.
Подробности и воспроизводимые команды: [сравнение](docs/comparison.md).

## Как строится граф

CLI проверяет параметры. Координаты переводятся в путь
`group/path/artifact/version/artifact-version.pom`. HTTP-клиент читает POM,
XML-парсер получает модель. При необходимости загружаются родительские POM
и BOM, наследуются поля, раскрываются свойства и применяются управляемые
версии. Координаты прямых зависимостей становятся соседями вершины.

`build_graph` обрабатывает весь текущий уровень и рекурсивно переходит
к следующему. `discovered` запоминает пакет при обнаружении, поэтому общие
зависимости и циклы не вызывают повторных загрузок. Ребра сохраняются.
Рекурсия выполняется блоками по 128 уровней; внешний цикл продолжает
длинную цепочку без изменения лимита Python. Resolver один на весь BFS,
его кэш хранит POM в памяти до завершения анализа.

После построения графа ASCII-режим печатает дерево. Обычный режим создает
DOT, вызывает Graphviz dot со списком аргументов без shell, проверяет
результат и открывает изображение. Тайм-аут Graphviz - 30 секунд.

### Ограничения


Поддерживаются явно заданные версии опубликованных POM в Maven layout.
Не реализованы выбор latest, разрешение диапазонов версий и поиск
timestamped SNAPSHOT по `maven-metadata.xml`. Строка `1.0-SNAPSHOT`
синтаксически принимается, но используется только прямой путь к такому POM.
Не активируются профили, свойства окружения и системные свойства Maven.
Не обрабатываются relocation, локальный `relativePath` родителя,
дополнительные репозитории внутри POM и правила транзитивных exclusions.
Обход включает объявления всех scope, в том числе test, provided и system,
а также optional-зависимости. Правила переноса scope на транзитивные пути
и выбора единственной версии при конфликтах не применяются.
Разные версии одного артефакта представлены разными вершинами.
type и classifier сохраняются парсером, вершина обозначается тремя
координатами groupId:artifactId:version. Варианты одного POM объединяются.
Неизвестное используемое свойство или отсутствующая версия дает ошибку,
а не неполную строку зависимости. Это учебный анализатор, не полная
реализация Maven effective POM.

## Демонстрация HTTP без внешнего интернета

В первом терминале из корня проекта:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory tests/fixtures/maven2
```

Во втором:

```powershell
python -m src --package g:app:1 --repository http://127.0.0.1:8000/ --ascii-tree
```

Здесь есть родительский POM, BOM, свойство версии, общая зависимость и цикл.
Чтобы увидеть изображение, уберите `--ascii-tree`. Сервер останавливается Ctrl+C.

## Ошибки и тесты

Коды завершения: 0 - успех, 1 - ошибка JSON/POM/сети/Graphviz,
2 - неправильные параметры. Ошибки выводятся в stderr без traceback,
частичный граф при ошибке загрузки не печатается.

```powershell
python -X utf8 -m unittest discover -s tests -v
```

110 тестов: 25 CLI, 3 точки входа, 10 простого POM, 10 HTTP-клиента,
7 свойств, 17 resolver, 4 HTTP-интеграции, 12 графа, 13 JSON и 9 визуализации.
Внешняя сеть и сторонние Python-библиотеки не нужны. Две проверки настоящего
Graphviz пропускаются, если dot не установлен. Остальные проверки используют
подстановку внешнего процесса. При установленном Graphviz проверяются
настоящие PNG/SVG и полный запуск CLI с сохранением изображения.

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
| `src/graph.py` | Рекурсивный BFS и текстовый вывод графа |
| `src/visualization.py` | DOT, PNG/SVG, поиск Graphviz и открытие картинки |
| `src/local_repository.py` | Чтение и проверка тестового JSON-репозитория |
| `examples/simple.pom` | Пример для отдельного простого парсера |
| `examples/repository.json` | Ветвящийся граф с общей зависимостью |
| `examples/cycle.json` | Цикл из трех вершин |
| `examples/self_cycle.json` | Петля A -> A |
| `examples/isolated.json` | Несвязанные компоненты |
| `tests/fixtures/maven2` | Небольшой HTTP-репозиторий для интеграции |
| `run.bat` | Запуск в Windows с сохранением кода завершения |

### CLI и настройки

- `build_parser()` описывает две обязательные опции, флаги и путь изображения.
- `add_output_options(parser)` добавляет ASCII, путь и отключение окна.
- `display_result(config, graph)` выбирает дерево или изображение.
- `parse_config(argv)` читает аргументы и превращает ошибки проверок в код `2`.
- `main(argv)` выбирает режим, запускает анализ, обрабатывает ошибки данных.
- `Config` хранит `package`, `repository`, `test_mode`, `ascii_tree`, `output`, `no_open`;
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
- `get_dependency_graph(package, repository)` запускает BFS с общим resolver;
  вложенная `load(name)` возвращает координаты соседей одной вершины.
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

### Граф и тестовый репозиторий

- `build_graph(root, load)` возвращает словарь списков соседей в порядке BFS.
- Вложенная `visit_level(frontier, remaining)` рекурсивно обрабатывает уровни.
- `reference_note(package, ancestors, shown)` отличает цикл от общей ссылки.
- `tree_lines(root, graph, ascii_tree)` формирует ветви и подписи через стек.
- `format_graph(root, graph, ascii_tree)` объединяет схему и порядок BFS.
- `unique_packages(pairs)` отклоняет повторные ключи в JSON.
- `validate_node(package, dependencies, graph)` проверяет вершину и ее ссылки.
- `load_test_repository(repository)` читает и проверяет весь JSON-репозиторий.
- `get_test_graph(package, repository)` проверяет корень и запускает BFS.

### Graphviz

- `dot_quote(value)` экранирует имя вершины для DOT.
- `format_dot(root, graph)` формирует все вершины и ребра, выделяет корень.
- `graphviz_executable()` ищет dot в PATH и стандартных каталогах Windows.
- `render_graph(root, graph, output)` сохраняет DOT и создает PNG или SVG.
- `open_graph(image)` открывает готовую картинку программой ОС или браузером.

## История этапов

| Этап | Коммит | Поведение |
| --- | --- | --- |
| 1 | d417e19 | Печать настроек |
| 2 | 1a33d87 | Прямые зависимости по HTTP |
| 3 | ef6cab7 | Рекурсивный BFS и текстовая схема |
| 5 | practice-2 | Graphviz по умолчанию, ASCII по флагу |

Перед переключением проверьте `git status`. В отдельном обычном клоне:

```powershell
git log --oneline --graph --decorate
git checkout d417e19
python -m src --package junit:junit:4.13.2 --repository https://repo1.maven.org/maven2/
git checkout 1a33d87
python -m src --package junit:junit:4.13.2 --repository https://repo1.maven.org/maven2/
git checkout ef6cab7
python -m src --package A --repository examples/repository.json --test-mode
git checkout practice-2
python -m src --package A --repository examples/repository.json --test-mode
```

На коммите Git сообщает detached HEAD: просмотр версии вне ветки.
Возврат к актуальной программе: `git checkout practice-2`.
На GitHub актуальный код находится в ветке practice-2.
