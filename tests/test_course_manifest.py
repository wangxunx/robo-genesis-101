import copy
import json
from pathlib import Path

import pytest

from robo_genesis.course_manifest import (
    CourseManifestError,
    CourseStatus,
    HardwareRequirement,
    load_course_manifest,
    validate_course_manifest,
)

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "course.json"


def _manifest_data() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_repository_manifest_defines_the_canonical_learning_path() -> None:
    manifest = load_course_manifest(MANIFEST_PATH)

    assert manifest.schema_version == 1
    assert manifest.course.id == "robo-genesis-101"
    assert manifest.course.default_locale == "zh"
    assert manifest.course.locales == ("zh", "en")
    assert [lesson.id for lesson in manifest.lessons] == [
        f"L{number:02d}" for number in range(1, 13)
    ]
    assert [lesson.status for lesson in manifest.lessons] == [
        CourseStatus.PLANNED,
        CourseStatus.CPU_VERIFIED,
        *([CourseStatus.PLANNED] * 8),
        CourseStatus.GPU_VERIFIED,
        CourseStatus.PLANNED,
    ]
    assert [lesson.hardware for lesson in manifest.lessons] == [
        *([HardwareRequirement.CPU_OK] * 6),
        *([HardwareRequirement.GPU_RECOMMENDED] * 4),
        *([HardwareRequirement.GPU_REQUIRED] * 2),
    ]


def test_course_status_enum_matches_the_public_contract() -> None:
    assert tuple(status.value for status in CourseStatus) == (
        "planned",
        "draft",
        "reviewed",
        "cpu-verified",
        "gpu-verified",
        "published",
    )


def test_manifest_paths_follow_the_bilingual_mapping() -> None:
    manifest = load_course_manifest(MANIFEST_PATH)

    for lesson in manifest.lessons:
        stem = f"{lesson.id.lower()}-{lesson.slug}"
        for locale in manifest.course.locales:
            assert lesson.lecture.for_locale(locale).as_posix() == (
                f"docs/{locale}/lessons/{stem}.md"
            )
            assert lesson.notebook.for_locale(locale).as_posix() == (
                f"notebooks/{locale}/{stem}.ipynb"
            )


def test_manifest_rejects_an_unknown_status() -> None:
    data = _manifest_data()
    data["lessons"][0]["status"] = "complete"

    with pytest.raises(CourseManifestError, match=r"lessons\[0\]\.status"):
        validate_course_manifest(data)


def test_manifest_rejects_an_unknown_hardware_requirement() -> None:
    data = _manifest_data()
    data["lessons"][0]["hardware"] = "accelerator-only"

    with pytest.raises(CourseManifestError, match=r"lessons\[0\]\.hardware"):
        validate_course_manifest(data)


def test_manifest_rejects_nonsequential_lesson_ids() -> None:
    data = _manifest_data()
    data["lessons"][1]["id"] = "L03"

    with pytest.raises(CourseManifestError, match="expected 'L02'"):
        validate_course_manifest(data)


def test_manifest_rejects_duplicate_slugs() -> None:
    data = _manifest_data()
    data["lessons"][1]["slug"] = data["lessons"][0]["slug"]
    stem = f"l02-{data['lessons'][1]['slug']}"
    for locale in ("zh", "en"):
        data["lessons"][1]["lecture"][locale] = f"docs/{locale}/lessons/{stem}.md"
        data["lessons"][1]["notebook"][locale] = f"notebooks/{locale}/{stem}.ipynb"

    with pytest.raises(CourseManifestError, match="lesson slugs must be unique"):
        validate_course_manifest(data)


def test_manifest_rejects_noncanonical_or_unsafe_paths() -> None:
    data = _manifest_data()
    data["lessons"][0]["lecture"]["zh"] = "../outside.md"

    with pytest.raises(CourseManifestError, match="repository-relative POSIX path"):
        validate_course_manifest(data)


def test_manifest_rejects_unknown_fields() -> None:
    data = copy.deepcopy(_manifest_data())
    data["lessons"][0]["progress"] = 0

    with pytest.raises(CourseManifestError, match=r"unexpected=\['progress'\]"):
        validate_course_manifest(data)
