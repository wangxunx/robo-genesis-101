import json
from pathlib import Path

from robo_genesis.course_validation import (
    _paired_relative_files,
    markdown_heading_levels,
    parse_frontmatter,
    validate_notebook_pair,
    validate_repository,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _notebook(code: str, *, outputs: list[object] | None = None) -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "overview",
                "metadata": {},
                "source": ["# Lesson\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "example",
                "metadata": {},
                "outputs": [] if outputs is None else outputs,
                "source": [code],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_repository_passes_all_course_gates() -> None:
    summary = validate_repository(PROJECT_ROOT)

    assert summary.lessons == 12
    assert summary.markdown_files >= 26
    assert summary.notebooks >= 24
    assert summary.python_files >= 1


def test_bilingual_project_documents_have_matching_heading_structure() -> None:
    readme_zh = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README_en.md").read_text(encoding="utf-8")

    assert markdown_heading_levels(readme_zh) == markdown_heading_levels(readme_en)

    for name in ("CONTRIBUTING.md", "CONTENT_GUIDE.md"):
        text = (PROJECT_ROOT / name).read_text(encoding="utf-8")
        zh_section = text.split("\n## 中文\n", maxsplit=1)[1].split(
            "\n## English\n", maxsplit=1
        )[0]
        en_section = text.split("\n## English\n", maxsplit=1)[1]
        assert markdown_heading_levels(zh_section) == markdown_heading_levels(en_section)


def test_frontmatter_and_heading_parser_ignore_fenced_examples() -> None:
    text = """---
lesson: L01
duration_minutes: 60
title: "A lesson: with a colon"
---

# Top level

```python
## Not a Markdown heading
```

## Real subsection
"""

    document = parse_frontmatter(text)

    assert document.frontmatter == {
        "lesson": "L01",
        "duration_minutes": 60,
        "title": "A lesson: with a colon",
    }
    assert markdown_heading_levels(text) == (1, 2)


def test_notebook_pair_rejects_code_drift_outputs_and_syntax(tmp_path: Path) -> None:
    zh_path = tmp_path / "zh.ipynb"
    en_path = tmp_path / "en.ipynb"
    zh_path.write_text(json.dumps(_notebook("value = 1\n")), encoding="utf-8")
    en_path.write_text(
        json.dumps(_notebook("value = (\n", outputs=[{"output_type": "stream"}])),
        encoding="utf-8",
    )

    errors = validate_notebook_pair(zh_path, en_path)

    assert any("committed outputs are not allowed" in error for error in errors)
    assert any("Python syntax error" in error for error in errors)
    assert any("code cell 1 sources differ" in error for error in errors)


def test_paired_files_ignore_jupyter_checkpoints(tmp_path: Path) -> None:
    for locale in ("zh", "en"):
        locale_directory = tmp_path / "notebooks" / locale
        locale_directory.mkdir(parents=True)
        (locale_directory / "lesson.ipynb").write_text("{}", encoding="utf-8")

    checkpoint_directory = tmp_path / "notebooks" / "en" / ".ipynb_checkpoints"
    checkpoint_directory.mkdir()
    (checkpoint_directory / "lesson-checkpoint.ipynb").write_text("{}", encoding="utf-8")

    errors: list[str] = []
    localized, relative_paths = _paired_relative_files(
        tmp_path,
        base_directory="notebooks",
        pattern="*.ipynb",
        errors=errors,
    )

    assert errors == []
    assert {path.as_posix() for path in relative_paths} == {"lesson.ipynb"}
    assert all(
        {path.as_posix() for path in files} == {"lesson.ipynb"}
        for files in localized.values()
    )
