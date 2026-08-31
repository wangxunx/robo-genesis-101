"""Repository-wide validation gates for the bilingual RoboGenesis course.

The validator intentionally uses only the Python standard library.  It can
therefore run after a dependency-light editable install on an ordinary GitHub
runner; Genesis, a GPU, course datasets, and long-running experiments are not
part of this gate.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import subprocess
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from .course_manifest import (
    CourseManifest,
    CourseManifestError,
    CourseStatus,
    Lesson,
    SUPPORTED_LOCALES,
    load_course_manifest,
)
from .paths import PROJECT_ROOT

FRONTMATTER_FIELDS = {
    "lesson",
    "slug",
    "locale",
    "title",
    "duration_minutes",
    "hardware",
    "status",
}
NOTEBOOK_METADATA_FIELDS = FRONTMATTER_FIELDS - {"title"}
IMPORT_SMOKE_MODULES = (
    "robo_genesis",
    "robo_genesis.course_manifest",
    "robo_genesis.paths",
    "robo_genesis.setup_assets",
    "robo_genesis.stats",
)

_CELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+\S", re.MULTILINE)
_INLINE_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]*)\)")
_REFERENCE_DEFINITION_PATTERN = re.compile(
    r"^\s*\[([^\]\n]+)\]:\s*(\S.*?)\s*$", re.MULTILINE
)
_REFERENCE_USE_PATTERN = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
_HTML_LINK_PATTERN = re.compile(
    r"\b(?:href|src)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE
)
_FRONTMATTER_LINK_PATTERN = re.compile(r"^\s*link:\s*(\S+)\s*$", re.MULTILINE)
_COURSE_ROW_PATTERN = re.compile(r"^\|\s*(L\d{2})\s*\|", re.MULTILINE)
_MARKDOWN_LINK_CELL_PATTERN = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")
_EMPTY_LINK_PATTERN = re.compile(
    r"\]\(\s*\)|\b(?:href|src)\s*=\s*([\"'])\s*\1|"
    r"^\s*(?:link|\[[^\]]+\]):\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_INLINE_CODE_PATTERN = re.compile(r"(`+)([^`\n]*?)\1")


@dataclass(frozen=True)
class CourseValidationSummary:
    """Counts returned after all repository gates pass."""

    lessons: int
    markdown_files: int
    notebooks: int
    python_files: int


class CourseValidationError(ValueError):
    """Raised with every repository validation failure found in one run."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__(f"{len(self.errors)} course validation error(s)")

    def __str__(self) -> str:
        details = "\n".join(f"  - {error}" for error in self.errors)
        return f"{super().__str__()}:\n{details}"


@dataclass(frozen=True)
class _MarkdownDocument:
    frontmatter: Mapping[str, object]
    body: str


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _source_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(line, str) for line in value):
        return "".join(value)
    raise TypeError("expected a string or an array of strings")


def _parse_frontmatter_scalar(raw_value: str) -> object:
    value = raw_value.strip()
    if not value:
        return ""
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_frontmatter(text: str, *, source: str = "<memory>") -> _MarkdownDocument:
    """Parse the flat YAML subset used by lesson frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{source}: missing opening frontmatter delimiter")

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        raise ValueError(f"{source}: missing closing frontmatter delimiter")

    metadata: dict[str, object] = {}
    for line_number, raw_line in enumerate(lines[1:closing_index], start=2):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, raw_value = line.partition(":")
        key = key.strip()
        if not separator or not key or key in metadata:
            raise ValueError(f"{source}:{line_number}: invalid flat frontmatter field")
        if raw_line[:1].isspace():
            raise ValueError(
                f"{source}:{line_number}: nested frontmatter is not supported for lessons"
            )
        metadata[key] = _parse_frontmatter_scalar(raw_value)

    return _MarkdownDocument(
        frontmatter=metadata,
        body="".join(lines[closing_index + 1 :]),
    )


def _without_fenced_code(text: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            output.append("\n")
        elif fence is None:
            output.append(line)
        else:
            output.append("\n")
    return "".join(output)


def markdown_heading_levels(text: str) -> tuple[int, ...]:
    """Return ATX heading levels, ignoring frontmatter and fenced code."""
    body = text
    if text.startswith("---"):
        try:
            body = parse_frontmatter(text).body
        except ValueError:
            pass
    clean_text = _without_fenced_code(body)
    return tuple(len(match.group(1)) for match in _HEADING_PATTERN.finditer(clean_text))


def _paired_relative_files(
    root: Path,
    *,
    base_directory: str,
    pattern: str,
    errors: list[str],
) -> tuple[dict[str, dict[PurePosixPath, Path]], set[PurePosixPath]]:
    localized: dict[str, dict[PurePosixPath, Path]] = {}
    for locale in SUPPORTED_LOCALES:
        directory = root / base_directory / locale
        if not directory.is_dir():
            errors.append(f"{directory.relative_to(root)}: locale directory is missing")
            localized[locale] = {}
            continue
        localized[locale] = {
            PurePosixPath(path.relative_to(directory).as_posix()): path
            for path in directory.rglob(pattern)
            if path.is_file()
        }

    union = set().union(*(set(files) for files in localized.values()))
    for relative_path in sorted(union):
        missing = [
            locale for locale in SUPPORTED_LOCALES if relative_path not in localized[locale]
        ]
        if missing:
            errors.append(
                f"{base_directory}/{{zh,en}}/{relative_path}: missing locale(s) {missing}"
            )
    return localized, union


def _expected_lesson_metadata(lesson: Lesson, locale: str) -> dict[str, object]:
    return {
        "lesson": lesson.id,
        "slug": lesson.slug,
        "locale": locale,
        "title": lesson.title.for_locale(locale),
        "duration_minutes": lesson.duration_minutes,
        "hardware": lesson.hardware.value,
        "status": lesson.status.value,
    }


def _validate_markdown_structure(
    root: Path,
    manifest: CourseManifest,
    errors: list[str],
) -> int:
    localized, relative_paths = _paired_relative_files(
        root,
        base_directory="docs",
        pattern="*.md",
        errors=errors,
    )

    for relative_path in sorted(relative_paths):
        if not all(relative_path in localized[locale] for locale in SUPPORTED_LOCALES):
            continue
        texts = {
            locale: localized[locale][relative_path].read_text(encoding="utf-8")
            for locale in SUPPORTED_LOCALES
        }
        levels = {locale: markdown_heading_levels(text) for locale, text in texts.items()}
        if levels["zh"] != levels["en"]:
            errors.append(
                f"docs/{{zh,en}}/{relative_path}: heading levels differ: "
                f"zh={levels['zh']}, en={levels['en']}"
            )

    for lesson in manifest.lessons:
        parsed: dict[str, _MarkdownDocument] = {}
        for locale in SUPPORTED_LOCALES:
            path = root / lesson.lecture.for_locale(locale)
            display = _display_path(path, root)
            if not path.is_file():
                errors.append(f"{display}: manifest-declared lecture is missing")
                continue
            try:
                document = parse_frontmatter(
                    path.read_text(encoding="utf-8"), source=display
                )
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(str(exc))
                continue
            parsed[locale] = document
            missing_fields = sorted(FRONTMATTER_FIELDS - set(document.frontmatter))
            if missing_fields:
                errors.append(f"{display}: missing frontmatter fields {missing_fields}")
            unexpected_fields = sorted(set(document.frontmatter) - FRONTMATTER_FIELDS)
            if unexpected_fields:
                errors.append(f"{display}: unexpected frontmatter fields {unexpected_fields}")
            expected = _expected_lesson_metadata(lesson, locale)
            for field, expected_value in expected.items():
                actual = document.frontmatter.get(field)
                if actual != expected_value:
                    errors.append(
                        f"{display}: frontmatter {field!r} is {actual!r}; "
                        f"expected {expected_value!r}"
                    )

        if set(parsed) == set(SUPPORTED_LOCALES):
            for field in ("lesson", "slug", "duration_minutes", "hardware", "status"):
                if parsed["zh"].frontmatter.get(field) != parsed["en"].frontmatter.get(field):
                    errors.append(
                        f"{lesson.id}: bilingual lecture frontmatter differs for {field!r}"
                    )
    return sum(len(files) for files in localized.values())


def _load_notebook(path: Path, *, root: Path, errors: list[str]) -> Mapping[str, Any] | None:
    display = _display_path(path, root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{display}: invalid notebook JSON: {exc}")
        return None
    if not isinstance(data, Mapping):
        errors.append(f"{display}: notebook root must be a JSON object")
        return None
    return data


def _notebook_cell_checks(
    notebook: Mapping[str, Any],
    *,
    path: Path,
    root: Path,
    errors: list[str],
) -> None:
    display = _display_path(path, root)
    if notebook.get("nbformat") != 4:
        errors.append(f"{display}: nbformat must be 4")
    minor_version = notebook.get("nbformat_minor")
    if isinstance(minor_version, bool) or not isinstance(minor_version, int) or minor_version < 0:
        errors.append(f"{display}: nbformat_minor must be a non-negative integer")
    if not isinstance(notebook.get("metadata"), Mapping):
        errors.append(f"{display}: metadata must be an object")
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        errors.append(f"{display}: cells must be an array")
        return

    seen_ids: set[str] = set()
    for index, cell in enumerate(cells):
        location = f"{display}: cell {index}"
        if not isinstance(cell, Mapping):
            errors.append(f"{location}: cell must be an object")
            continue
        cell_type = cell.get("cell_type")
        if cell_type not in {"markdown", "code", "raw"}:
            errors.append(f"{location}: unsupported cell_type {cell_type!r}")
        if not isinstance(cell.get("metadata"), Mapping):
            errors.append(f"{location}: metadata must be an object")
        cell_id = cell.get("id")
        if not isinstance(cell_id, str) or not _CELL_ID_PATTERN.fullmatch(cell_id):
            errors.append(f"{location}: missing or invalid cell id")
        elif cell_id in seen_ids:
            errors.append(f"{location}: duplicate cell id {cell_id!r}")
        else:
            seen_ids.add(cell_id)
        try:
            source = _source_text(cell.get("source"))
        except TypeError as exc:
            errors.append(f"{location}: {exc}")
            continue
        if cell_type == "code":
            if cell.get("execution_count") is not None:
                errors.append(f"{location}: execution_count must be null")
            if cell.get("outputs") != []:
                errors.append(f"{location}: committed outputs are not allowed")
            try:
                compile(source, f"{display} cell {index}", "exec")
            except SyntaxError as exc:
                errors.append(
                    f"{location}: Python syntax error at line {exc.lineno}: {exc.msg}"
                )


def validate_notebook_pair(zh_path: Path, en_path: Path) -> tuple[str, ...]:
    """Validate the structural and executable parity of one notebook pair."""
    root = Path.cwd().resolve()
    errors: list[str] = []
    notebooks = {
        "zh": _load_notebook(Path(zh_path), root=root, errors=errors),
        "en": _load_notebook(Path(en_path), root=root, errors=errors),
    }
    for locale, notebook in notebooks.items():
        if notebook is not None:
            _notebook_cell_checks(
                notebook,
                path=Path(zh_path if locale == "zh" else en_path),
                root=root,
                errors=errors,
            )
    _compare_notebook_pair(notebooks, label=f"{zh_path} / {en_path}", errors=errors)
    return tuple(errors)


def _compare_notebook_pair(
    notebooks: Mapping[str, Mapping[str, Any] | None],
    *,
    label: str,
    errors: list[str],
) -> None:
    if any(notebooks.get(locale) is None for locale in SUPPORTED_LOCALES):
        return
    zh_notebook = notebooks["zh"]
    en_notebook = notebooks["en"]
    assert zh_notebook is not None and en_notebook is not None
    zh_cells = zh_notebook.get("cells")
    en_cells = en_notebook.get("cells")
    if not isinstance(zh_cells, list) or not isinstance(en_cells, list):
        return
    zh_types = tuple(
        cell.get("cell_type") if isinstance(cell, Mapping) else None for cell in zh_cells
    )
    en_types = tuple(
        cell.get("cell_type") if isinstance(cell, Mapping) else None for cell in en_cells
    )
    if zh_types != en_types:
        errors.append(f"{label}: bilingual cell type sequences differ")
        return

    for index, (zh_cell, en_cell) in enumerate(zip(zh_cells, en_cells, strict=True)):
        if not isinstance(zh_cell, Mapping) or not isinstance(en_cell, Mapping):
            continue
        if zh_cell.get("cell_type") == "code":
            if zh_cell.get("id") != en_cell.get("id"):
                errors.append(f"{label}: code cell {index} ids differ")
            try:
                same_source = _source_text(zh_cell.get("source")) == _source_text(
                    en_cell.get("source")
                )
            except TypeError:
                same_source = False
            if not same_source:
                errors.append(f"{label}: code cell {index} sources differ")

    def notebook_headings(cells: list[object]) -> tuple[int, ...]:
        headings: list[int] = []
        for cell in cells:
            if isinstance(cell, Mapping) and cell.get("cell_type") == "markdown":
                try:
                    headings.extend(markdown_heading_levels(_source_text(cell.get("source"))))
                except TypeError:
                    pass
        return tuple(headings)

    zh_headings = notebook_headings(zh_cells)
    en_headings = notebook_headings(en_cells)
    if zh_headings != en_headings:
        errors.append(
            f"{label}: markdown heading levels differ: "
            f"zh={zh_headings}, en={en_headings}"
        )


def _validate_notebooks(
    root: Path,
    manifest: CourseManifest,
    errors: list[str],
) -> tuple[int, list[tuple[str, str]], list[tuple[Path, str, str]]]:
    localized, relative_paths = _paired_relative_files(
        root,
        base_directory="notebooks",
        pattern="*.ipynb",
        errors=errors,
    )
    loaded: dict[Path, Mapping[str, Any] | None] = {}
    notebook_code: list[tuple[str, str]] = []
    notebook_markdown: list[tuple[Path, str, str]] = []
    for locale in SUPPORTED_LOCALES:
        for path in localized[locale].values():
            notebook = _load_notebook(path, root=root, errors=errors)
            loaded[path] = notebook
            if notebook is None:
                continue
            _notebook_cell_checks(notebook, path=path, root=root, errors=errors)
            cells = notebook.get("cells")
            if isinstance(cells, list):
                for index, cell in enumerate(cells):
                    if not isinstance(cell, Mapping):
                        continue
                    try:
                        source = _source_text(cell.get("source"))
                    except TypeError:
                        continue
                    label = f"{_display_path(path, root)}: cell {index}"
                    if cell.get("cell_type") == "code":
                        notebook_code.append((label, source))
                    elif cell.get("cell_type") == "markdown":
                        notebook_markdown.append((path, label, source))

    for relative_path in sorted(relative_paths):
        if not all(relative_path in localized[locale] for locale in SUPPORTED_LOCALES):
            continue
        pair = {
            locale: loaded.get(localized[locale][relative_path])
            for locale in SUPPORTED_LOCALES
        }
        _compare_notebook_pair(
            pair,
            label=f"notebooks/{{zh,en}}/{relative_path}",
            errors=errors,
        )

    for lesson in manifest.lessons:
        for locale in SUPPORTED_LOCALES:
            path = root / lesson.notebook.for_locale(locale)
            display = _display_path(path, root)
            if not path.is_file():
                errors.append(f"{display}: manifest-declared notebook is missing")
                continue
            notebook = loaded.get(path)
            if notebook is None:
                continue
            metadata = notebook.get("metadata")
            course_metadata = (
                metadata.get("robo_genesis") if isinstance(metadata, Mapping) else None
            )
            if not isinstance(course_metadata, Mapping):
                errors.append(f"{display}: metadata.robo_genesis must be an object")
                continue
            missing_fields = sorted(NOTEBOOK_METADATA_FIELDS - set(course_metadata))
            if missing_fields:
                errors.append(
                    f"{display}: missing metadata.robo_genesis fields {missing_fields}"
                )
            unexpected_fields = sorted(set(course_metadata) - NOTEBOOK_METADATA_FIELDS)
            if unexpected_fields:
                errors.append(
                    f"{display}: unexpected metadata.robo_genesis fields "
                    f"{unexpected_fields}"
                )
            expected = _expected_lesson_metadata(lesson, locale)
            expected.pop("title")
            for field, expected_value in expected.items():
                actual = course_metadata.get(field)
                if actual != expected_value:
                    errors.append(
                        f"{display}: metadata.robo_genesis {field!r} is {actual!r}; "
                        f"expected {expected_value!r}"
                    )
    return (
        sum(len(files) for files in localized.values()),
        notebook_code,
        notebook_markdown,
    )


def _markdown_sources(root: Path) -> tuple[Path, ...]:
    sources = list((root / "docs").rglob("*.md"))
    for name in ("README.md", "README_en.md"):
        path = root / name
        if path.is_file():
            sources.append(path)
    return tuple(sorted(path for path in sources if path.is_file()))


def _normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")].strip()
    return target.split(maxsplit=1)[0] if target else ""


def _local_link_candidates(root: Path, source: Path, target: str) -> tuple[Path, ...]:
    split = urlsplit(target)
    path_text = unquote(split.path)
    if not path_text:
        return ()
    if path_text.startswith("/"):
        relative = path_text.lstrip("/")
        base_candidate = root / "docs" / relative
        public_candidate = root / "docs" / "public" / relative
        candidates = [public_candidate, base_candidate]
    else:
        candidates = [source.parent / path_text]

    expanded: list[Path] = []
    for candidate in candidates:
        expanded.append(candidate)
        if candidate.suffix == "":
            expanded.extend((candidate.with_suffix(".md"), candidate / "index.md"))
        elif candidate.suffix == ".html":
            expanded.append(candidate.with_suffix(".md"))
    return tuple(expanded)


def _link_resolves(root: Path, source: Path, target: str) -> bool:
    split = urlsplit(target)
    if split.scheme or split.netloc or target.startswith(("#", "//")):
        return True
    for candidate in _local_link_candidates(root, source, target):
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            return True
    return False


def _validate_markdown_text_links(
    root: Path,
    *,
    source_path: Path,
    display: str,
    text: str,
    errors: list[str],
) -> None:
    clean_text = _without_fenced_code(text)
    clean_text = _INLINE_CODE_PATTERN.sub("", clean_text)
    definitions = {
        match.group(1).strip().casefold(): _normalize_link_target(match.group(2))
        for match in _REFERENCE_DEFINITION_PATTERN.finditer(clean_text)
    }
    targets: list[str] = [
        _normalize_link_target(match.group(1))
        for match in _INLINE_LINK_PATTERN.finditer(clean_text)
    ]
    targets.extend(
        match.group(2).strip() for match in _HTML_LINK_PATTERN.finditer(clean_text)
    )
    targets.extend(
        _normalize_link_target(match.group(1))
        for match in _FRONTMATTER_LINK_PATTERN.finditer(clean_text)
    )
    targets.extend(definitions.values())

    for match in _REFERENCE_USE_PATTERN.finditer(clean_text):
        reference = (match.group(2) or match.group(1)).strip().casefold()
        if reference not in definitions:
            errors.append(f"{display}: unresolved Markdown reference [{reference}]")

    for target in targets:
        if not target:
            continue
        if not _link_resolves(root, source_path, target):
            errors.append(f"{display}: local link does not resolve: {target!r}")


def _validate_markdown_links(
    root: Path,
    notebook_markdown: Iterable[tuple[Path, str, str]],
    errors: list[str],
) -> None:
    for path in _markdown_sources(root):
        _validate_markdown_text_links(
            root,
            source_path=path,
            display=_display_path(path, root),
            text=path.read_text(encoding="utf-8"),
            errors=errors,
        )
    for path, display, text in notebook_markdown:
        _validate_markdown_text_links(
            root,
            source_path=path,
            display=display,
            text=text,
            errors=errors,
        )


def _parse_course_rows(text: str, *, source: str, errors: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not _COURSE_ROW_PATTERN.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            errors.append(f"{source}:{line_number}: malformed course table row")
            continue
        link_match = _MARKDOWN_LINK_CELL_PATTERN.fullmatch(cells[1])
        if link_match is None:
            errors.append(f"{source}:{line_number}: lesson title must be a Markdown link")
            continue
        row = {
            "lesson": cells[0],
            "title": link_match.group(1),
            "target": link_match.group(2),
            "status": cells[-1].strip("` "),
        }
        if len(cells) >= 5:
            row["duration"] = cells[2]
            row["hardware"] = cells[3].strip("` ")
        rows.append(row)
    return rows


def _validate_course_table(
    root: Path,
    manifest: CourseManifest,
    *,
    path: Path,
    locale: str,
    website_routes: bool,
    errors: list[str],
) -> None:
    display = _display_path(path, root)
    if not path.is_file():
        errors.append(f"{display}: required course overview is missing")
        return
    rows = _parse_course_rows(
        path.read_text(encoding="utf-8"), source=display, errors=errors
    )
    expected_ids = [lesson.id for lesson in manifest.lessons]
    actual_ids = [row["lesson"] for row in rows]
    if actual_ids != expected_ids:
        errors.append(
            f"{display}: course table lesson order is {actual_ids}; expected {expected_ids}"
        )
        return

    for lesson, row in zip(manifest.lessons, rows, strict=True):
        expected_title = lesson.title.for_locale(locale)
        lecture_path = lesson.lecture.for_locale(locale).as_posix()
        expected_target = (
            f"/{lecture_path.removeprefix('docs/').removesuffix('.md')}"
            if website_routes
            else lecture_path
        )
        if row["title"] != expected_title:
            errors.append(
                f"{display}: {lesson.id} title is {row['title']!r}; expected {expected_title!r}"
            )
        if row["target"] != expected_target:
            errors.append(
                f"{display}: {lesson.id} target is {row['target']!r}; "
                f"expected {expected_target!r}"
            )
        if row["status"] != lesson.status.value:
            errors.append(
                f"{display}: {lesson.id} status is {row['status']!r}; "
                f"expected {lesson.status.value!r}"
            )
        if "duration" in row:
            expected_duration = (
                f"{lesson.duration_minutes} 分钟"
                if locale == "zh"
                else f"{lesson.duration_minutes} min"
            )
            if row["duration"] != expected_duration:
                errors.append(
                    f"{display}: {lesson.id} duration is {row['duration']!r}; "
                    f"expected {expected_duration!r}"
                )
            if row["hardware"] != lesson.hardware.value:
                errors.append(
                    f"{display}: {lesson.id} hardware is {row['hardware']!r}; "
                    f"expected {lesson.hardware.value!r}"
                )


def _validate_overview_tables(
    root: Path,
    manifest: CourseManifest,
    errors: list[str],
) -> None:
    _validate_course_table(
        root,
        manifest,
        path=root / "docs" / "zh" / "index.md",
        locale="zh",
        website_routes=True,
        errors=errors,
    )
    _validate_course_table(
        root,
        manifest,
        path=root / "docs" / "en" / "index.md",
        locale="en",
        website_routes=True,
        errors=errors,
    )
    _validate_course_table(
        root,
        manifest,
        path=root / "README.md",
        locale="zh",
        website_routes=False,
        errors=errors,
    )
    readme_en = root / "README_en.md"
    if readme_en.is_file():
        _validate_course_table(
            root,
            manifest,
            path=readme_en,
            locale="en",
            website_routes=False,
            errors=errors,
        )


def _published_placeholder_patterns(locale: str) -> tuple[re.Pattern[str], ...]:
    common = (
        re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b", re.IGNORECASE),
        _EMPTY_LINK_PATTERN,
    )
    if locale == "zh":
        return common + (
            re.compile(r"结构骨架|规划中|占位(?:内容|文本|页面)?"),
            re.compile(r"待(?:补充|完善|编写)|即将推出|模板(?:文案|内容)"),
            re.compile(r"将在.{0,30}(?:完成|开发|补充)"),
        )
    return common + (
        re.compile(r"\bstructural scaffold\b", re.IGNORECASE),
        re.compile(r"\bcurrently planned\b", re.IGNORECASE),
        re.compile(r"\bcoming soon\b|\blorem ipsum\b", re.IGNORECASE),
        re.compile(r"\btemplate (?:copy|content|text)\b", re.IGNORECASE),
        re.compile(r"\bwill be (?:developed|completed|added)\b", re.IGNORECASE),
    )


def _validate_published_content(
    root: Path,
    manifest: CourseManifest,
    errors: list[str],
) -> None:
    for lesson in manifest.lessons:
        if lesson.status is not CourseStatus.PUBLISHED:
            continue
        for locale in SUPPORTED_LOCALES:
            lecture = root / lesson.lecture.for_locale(locale)
            notebook = root / lesson.notebook.for_locale(locale)
            contents: list[tuple[str, str]] = []
            if lecture.is_file():
                contents.append((_display_path(lecture, root), lecture.read_text(encoding="utf-8")))
            if notebook.is_file():
                notebook_data = _load_notebook(notebook, root=root, errors=errors)
                if notebook_data is not None and isinstance(notebook_data.get("cells"), list):
                    cell_sources: list[str] = []
                    for cell in notebook_data["cells"]:
                        if not isinstance(cell, Mapping):
                            continue
                        try:
                            cell_sources.append(_source_text(cell.get("source")))
                        except TypeError:
                            continue
                    contents.append(
                        (_display_path(notebook, root), "\n".join(cell_sources))
                    )
            for display, text in contents:
                for pattern in _published_placeholder_patterns(locale):
                    match = pattern.search(text)
                    if match:
                        errors.append(
                            f"{display}: published content contains placeholder {match.group(0)!r}"
                        )


class _SysPathMutationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.sys_aliases = {"sys"}
        self.path_aliases: set[str] = set()
        self.lines: list[int] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if alias.name == "sys":
                self.sys_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module == "sys":
            for alias in node.names:
                if alias.name == "path":
                    self.path_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr in {"append", "extend", "insert"}:
            target = function.value
            direct_alias = isinstance(target, ast.Name) and target.id in self.path_aliases
            sys_attribute = (
                isinstance(target, ast.Attribute)
                and target.attr == "path"
                and isinstance(target.value, ast.Name)
                and target.value.id in self.sys_aliases
            )
            if direct_alias or sys_attribute:
                self.lines.append(node.lineno)
        self.generic_visit(node)

    def _is_path_target(self, target: ast.expr) -> bool:
        if isinstance(target, ast.Subscript):
            return self._is_path_target(target.value)
        if isinstance(target, ast.Name):
            return target.id in self.path_aliases
        return (
            isinstance(target, ast.Attribute)
            and target.attr == "path"
            and isinstance(target.value, ast.Name)
            and target.value.id in self.sys_aliases
        )

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        if any(self._is_path_target(target) for target in node.targets):
            self.lines.append(node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if self._is_path_target(node.target):
            self.lines.append(node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        if self._is_path_target(node.target):
            self.lines.append(node.lineno)
        self.generic_visit(node)


def _unsafe_source_issues(source: str, *, label: str) -> list[str]:
    issues: list[str] = []
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError:
        return issues
    visitor = _SysPathMutationVisitor()
    visitor.visit(tree)
    for line_number in visitor.lines:
        issues.append(f"{label}:{line_number}: sys.path mutation is not allowed")

    forbidden_fragments = {
        "/" + "home" + "/": "Linux developer absolute path",
        "/" + "Users" + "/": "macOS developer absolute path",
        "franka_fruit_pick" + "_demo": "source repository name",
        "hello" + "-genesis-world": "source repository name",
    }
    windows_user_pattern = re.compile(r"[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]", re.I)
    repository_parent_pattern = re.compile(r"(?<!\.)\.\.[/\\]")
    for line_number, line in enumerate(source.splitlines(), start=1):
        for fragment, description in forbidden_fragments.items():
            if fragment in line:
                issues.append(f"{label}:{line_number}: {description} is not allowed")
        if windows_user_pattern.search(line):
            issues.append(f"{label}:{line_number}: Windows developer absolute path is not allowed")
        if repository_parent_pattern.search(line):
            issues.append(f"{label}:{line_number}: repository-parent path is not allowed")
    return issues


def _validate_python_sources(
    root: Path,
    notebook_code: Iterable[tuple[str, str]],
    errors: list[str],
) -> int:
    paths = tuple(
        sorted(
            path
            for directory in (root / "src", root / "scripts", root / "tests")
            if directory.is_dir()
            for path in directory.rglob("*.py")
            if path.is_file()
        )
    )
    for path in paths:
        display = _display_path(path, root)
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, display, "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{display}: Python source cannot compile: {exc}")
            continue
        if path.is_relative_to(root / "src") or path.is_relative_to(root / "scripts"):
            errors.extend(_unsafe_source_issues(source, label=display))

    for label, source in notebook_code:
        errors.extend(_unsafe_source_issues(source, label=label))
    return len(paths)


def _dependency_strings(data: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    project = data.get("project")
    if isinstance(project, Mapping):
        dependencies = project.get("dependencies", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if isinstance(dependency, str):
                    yield "project.dependencies", dependency
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, Mapping):
            for group, values in optional.items():
                if isinstance(values, list):
                    for dependency in values:
                        if isinstance(dependency, str):
                            yield f"project.optional-dependencies.{group}", dependency
    groups = data.get("dependency-groups", {})
    if isinstance(groups, Mapping):
        for group, values in groups.items():
            if isinstance(values, list):
                for dependency in values:
                    if isinstance(dependency, str):
                        yield f"dependency-groups.{group}", dependency


def _validate_dependencies(root: Path, errors: list[str]) -> None:
    pyproject_path = root / "pyproject.toml"
    lock_path = root / "uv.lock"
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"pyproject.toml: cannot parse dependency metadata: {exc}")
        return

    unsafe_dependency = re.compile(
        r"(?:git\+|(?:https?|ssh)://\S+\.git(?:@|#|$)|@\s*(?:file:|\.?\.?/|/))",
        re.IGNORECASE,
    )
    for location, dependency in _dependency_strings(pyproject):
        if unsafe_dependency.search(dependency):
            errors.append(f"pyproject.toml: {location} uses a Git or local path dependency")

    tool = pyproject.get("tool")
    uv = tool.get("uv") if isinstance(tool, Mapping) else None
    sources = uv.get("sources") if isinstance(uv, Mapping) else None
    if isinstance(sources, Mapping):
        for package, source in sources.items():
            if isinstance(source, Mapping) and set(source) & {
                "git",
                "path",
                "directory",
                "editable",
            }:
                errors.append(
                    f"pyproject.toml: tool.uv.sources.{package} uses a Git or local path source"
                )

    try:
        lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"uv.lock: cannot parse lockfile: {exc}")
        return
    packages = lock.get("package")
    if not isinstance(packages, list):
        errors.append("uv.lock: package must be an array")
        return
    for package in packages:
        if not isinstance(package, Mapping):
            continue
        name = package.get("name", "<unknown>")
        source = package.get("source")
        if not isinstance(source, Mapping):
            continue
        disallowed = set(source) & {"git", "path", "directory"}
        editable = source.get("editable")
        expected_project_editable = name == "robo-genesis-101" and editable == "."
        if disallowed or (editable is not None and not expected_project_editable):
            errors.append(f"uv.lock: package {name!r} uses a Git or external local source")

    package_json_path = root / "package.json"
    package_lock_path = root / "package-lock.json"
    try:
        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        package_lock = json.loads(package_lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"npm dependency metadata cannot be parsed: {exc}")
        return
    npm_unsafe_source = re.compile(
        r"^(?:git\+|git://|github:|file:|link:|workspace:|\.?\.?/|/)|"
        r"^https?://\S+\.git(?:#|$)",
        re.IGNORECASE,
    )
    if isinstance(package_json, Mapping):
        for group in ("dependencies", "devDependencies", "optionalDependencies"):
            dependencies = package_json.get(group)
            if not isinstance(dependencies, Mapping):
                continue
            for package, source in dependencies.items():
                if isinstance(source, str) and npm_unsafe_source.search(source):
                    errors.append(
                        f"package.json: {group}.{package} uses a Git or local path source"
                    )
    lock_packages = package_lock.get("packages") if isinstance(package_lock, Mapping) else None
    if isinstance(lock_packages, Mapping):
        for location, package in lock_packages.items():
            if not isinstance(package, Mapping):
                continue
            resolved = package.get("resolved")
            if package.get("link") is True or (
                isinstance(resolved, str) and npm_unsafe_source.search(resolved)
            ):
                errors.append(
                    f"package-lock.json: {location or '<root>'} uses a Git or local path source"
                )


def _validate_submodules(root: Path, errors: list[str]) -> None:
    if (root / ".gitmodules").exists():
        errors.append(".gitmodules: Git submodules are not allowed")
    if not (root / ".git").exists():
        return
    try:
        result = subprocess.run(
            ["git", "ls-files", "--stage"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"git ls-files --stage: cannot inspect submodules: {exc}")
        return
    for line in result.stdout.splitlines():
        if line.startswith("160000 "):
            errors.append(f"Git submodule entry is not allowed: {line.split(maxsplit=3)[-1]}")


def _validate_imports(errors: list[str]) -> None:
    for module_name in IMPORT_SMOKE_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - exact import failures vary
            errors.append(f"cannot import {module_name}: {type(exc).__name__}: {exc}")


def validate_repository(root: Path | str = PROJECT_ROOT) -> CourseValidationSummary:
    """Run all M1.9 course gates and return counts, or raise one aggregate error."""
    repository_root = Path(root).resolve()
    errors: list[str] = []
    try:
        manifest = load_course_manifest(repository_root / "course.json")
    except CourseManifestError as exc:
        raise CourseValidationError([str(exc)]) from exc

    markdown_count = _validate_markdown_structure(repository_root, manifest, errors)
    notebook_count, notebook_code, notebook_markdown = _validate_notebooks(
        repository_root, manifest, errors
    )
    _validate_markdown_links(repository_root, notebook_markdown, errors)
    _validate_overview_tables(repository_root, manifest, errors)
    _validate_published_content(repository_root, manifest, errors)
    python_count = _validate_python_sources(repository_root, notebook_code, errors)
    _validate_dependencies(repository_root, errors)
    _validate_submodules(repository_root, errors)
    _validate_imports(errors)

    if errors:
        raise CourseValidationError(errors)
    return CourseValidationSummary(
        lessons=len(manifest.lessons),
        markdown_files=markdown_count,
        notebooks=notebook_count,
        python_files=python_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate RoboGenesis bilingual course structure and repository safety."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root (default: the current RoboGenesis checkout).",
    )
    args = parser.parse_args()
    try:
        summary = validate_repository(args.root)
    except CourseValidationError as exc:
        parser.exit(1, f"Course validation failed:\n{exc}\n")
    print(
        "Course validation passed: "
        f"{summary.lessons} lessons, "
        f"{summary.markdown_files} localized Markdown files, "
        f"{summary.notebooks} notebooks, "
        f"{summary.python_files} Python files."
    )


if __name__ == "__main__":
    main()
