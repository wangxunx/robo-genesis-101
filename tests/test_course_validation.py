import json
from pathlib import Path

from robo_genesis.course_validation import (
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
