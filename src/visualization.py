"""Экспорт графа в DOT, построение изображения Graphviz и его открытие."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser


IMAGE_FORMATS = {".png": "png", ".svg": "svg"}
RENDER_TIMEOUT_SECONDS = 30


def dot_quote(value: str) -> str:
    """Экранировать название вершины как строку языка DOT."""
    return json.dumps(value, ensure_ascii=False)


def format_dot(root: str, graph: dict[str, list[str]]) -> str:
    """Сохранить все вершины и ребра, включая общие связи и циклы."""
    lines = ["digraph dependencies {", "  rankdir=LR;",
             '  node [shape=box, fontname="Arial"];']
    for package in graph:
        style = (' [style=filled, fillcolor="lightblue"]'
                 if package == root else "")
        lines.append(f"  {dot_quote(package)}{style};")
    for package, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(f"  {dot_quote(package)} -> "
                         f"{dot_quote(dependency)};")
    return "\n".join([*lines, "}", ""])


def graphviz_executable() -> str:
    """Найти dot в PATH или в стандартных каталогах Windows."""
    executable = shutil.which("dot")
    if executable:
        return executable
    folders = [("ProgramFiles", "Graphviz"),
               ("ProgramFiles(x86)", "Graphviz"),
               ("LOCALAPPDATA", "Programs/Graphviz")]
    for variable, folder in folders:
        if os.environ.get(variable):
            path = Path(os.environ[variable]) / folder / "bin" / "dot.exe"
            if path.is_file():
                return str(path)
    raise ValueError("Graphviz не найден: установите Graphviz "
                     "или используйте --ascii-tree")


def render_graph(root: str, graph: dict, output: str) -> Path:
    """Записать DOT и создать PNG или SVG через внешний Graphviz dot."""
    image = Path(output).expanduser().resolve()
    image_format = IMAGE_FORMATS.get(image.suffix.lower())
    if not image_format:
        raise ValueError("--output: требуется файл с расширением .png или .svg")
    executable = graphviz_executable()
    dot_file = image.with_suffix(".dot")
    try:
        image.parent.mkdir(parents=True, exist_ok=True)
        dot_file.write_text(format_dot(root, graph), encoding="utf-8")
        result = subprocess.run(
            [executable, f"-T{image_format}", str(dot_file), "-o", str(image)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=RENDER_TIMEOUT_SECONDS, check=False,
        )
        if result.returncode:
            raise ValueError("Graphviz: " + result.stderr.strip())
        if not image.is_file() or not image.stat().st_size:
            raise ValueError("Graphviz не создал изображение")
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(
            f"не удалось построить изображение: {error}"
        ) from error
    return image


def open_graph(image: Path) -> None:
    """Открыть изображение программой ОС или браузером."""
    try:
        if sys.platform == "win32":
            os.startfile(str(image))
        elif not webbrowser.open(image.as_uri()):
            raise ValueError(f"откройте изображение вручную: {image}")
    except OSError as error:
        raise ValueError(f"не удалось открыть изображение {image}") from error
