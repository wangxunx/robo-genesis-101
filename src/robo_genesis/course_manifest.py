"""Typed reader and validator for the canonical ``course.json`` manifest.

M1.6 validates metadata and canonical target paths only. Lesson and notebook
existence becomes enforceable after their skeletons are created in M1.7.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, TypeVar

from .paths import PROJECT_ROOT, resolve_cli_path

SCHEMA_VERSION = 1
SUPPORTED_LOCALES = ("zh", "en")
LESSON_COUNT = 12
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "course.json"

_COURSE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LESSON_ID_PATTERN = re.compile(r"^L\d{2}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

EnumValue = TypeVar("EnumValue", bound=StrEnum)


class CourseManifestError(ValueError):
    """Raised when course metadata does not satisfy the repository contract."""


class CourseStatus(StrEnum):
    """Allowed publication states, ordered from planning through release."""

    PLANNED = "planned"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    CPU_VERIFIED = "cpu-verified"
    GPU_VERIFIED = "gpu-verified"
    PUBLISHED = "published"


class HardwareRequirement(StrEnum):
    """Hardware level expected for a lesson's complete hands-on path."""

    CPU_OK = "cpu-ok"
    GPU_RECOMMENDED = "gpu-recommended"
    GPU_REQUIRED = "gpu-required"


@dataclass(frozen=True)
class LocalizedText:
    zh: str
    en: str

    def for_locale(self, locale: str) -> str:
        if locale not in SUPPORTED_LOCALES:
            raise KeyError(f"Unsupported locale: {locale}")
        return getattr(self, locale)


@dataclass(frozen=True)
class LocalizedPaths:
    zh: PurePosixPath
    en: PurePosixPath

    def for_locale(self, locale: str) -> PurePosixPath:
        if locale not in SUPPORTED_LOCALES:
            raise KeyError(f"Unsupported locale: {locale}")
        return getattr(self, locale)


@dataclass(frozen=True)
class CourseInfo:
    id: str
    title: LocalizedText
    default_locale: str
    locales: tuple[str, ...]


@dataclass(frozen=True)
class Lesson:
    id: str
    slug: str
    title: LocalizedText
    duration_minutes: int
    hardware: HardwareRequirement
    notebook: LocalizedPaths
    lecture: LocalizedPaths
    status: CourseStatus


@dataclass(frozen=True)
class CourseManifest:
    schema_version: int
    course: CourseInfo
    lessons: tuple[Lesson, ...]

    def lesson(self, lesson_id: str) -> Lesson:
        """Return a lesson by its stable ID."""
        for lesson in self.lessons:
            if lesson.id == lesson_id:
                return lesson
        raise KeyError(f"Unknown lesson id: {lesson_id}")


def _fail(source: str, location: str, message: str) -> NoReturn:
    raise CourseManifestError(f"{source}: {location}: {message}")


def _object(value: object, *, source: str, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(source, location, "expected an object")
    return value


def _keys(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    source: str,
    location: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        _fail(
            source,
            location,
            f"invalid keys; missing={missing}, unexpected={unexpected}",
        )


def _string(value: object, *, source: str, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(source, location, "expected a non-empty string")
    return value


def _localized_text(value: object, *, source: str, location: str) -> LocalizedText:
    mapping = _object(value, source=source, location=location)
    _keys(mapping, set(SUPPORTED_LOCALES), source=source, location=location)
    return LocalizedText(
        zh=_string(mapping["zh"], source=source, location=f"{location}.zh"),
        en=_string(mapping["en"], source=source, location=f"{location}.en"),
    )


def _relative_path(value: object, *, source: str, location: str) -> PurePosixPath:
    raw_path = _string(value, source=source, location=location)
    path = PurePosixPath(raw_path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in raw_path
        or path.as_posix() != raw_path
    ):
        _fail(source, location, "expected a normalized repository-relative POSIX path")
    return path


def _localized_paths(value: object, *, source: str, location: str) -> LocalizedPaths:
    mapping = _object(value, source=source, location=location)
    _keys(mapping, set(SUPPORTED_LOCALES), source=source, location=location)
    return LocalizedPaths(
        zh=_relative_path(mapping["zh"], source=source, location=f"{location}.zh"),
        en=_relative_path(mapping["en"], source=source, location=f"{location}.en"),
    )


def _enum_value(
    enum_type: type[EnumValue],
    value: object,
    *,
    source: str,
    location: str,
) -> EnumValue:
    raw_value = _string(value, source=source, location=location)
    try:
        return enum_type(raw_value)
    except ValueError:
        allowed = [member.value for member in enum_type]
        _fail(source, location, f"expected one of {allowed}, got {raw_value!r}")


def _lesson(value: object, *, index: int, source: str) -> Lesson:
    location = f"lessons[{index}]"
    mapping = _object(value, source=source, location=location)
    _keys(
        mapping,
        {
            "id",
            "slug",
            "title",
            "duration_minutes",
            "hardware",
            "notebook",
            "lecture",
            "status",
        },
        source=source,
        location=location,
    )

    lesson_id = _string(mapping["id"], source=source, location=f"{location}.id")
    expected_id = f"L{index + 1:02d}"
    if not _LESSON_ID_PATTERN.fullmatch(lesson_id) or lesson_id != expected_id:
        _fail(source, f"{location}.id", f"expected {expected_id!r}, got {lesson_id!r}")

    slug = _string(mapping["slug"], source=source, location=f"{location}.slug")
    if not _SLUG_PATTERN.fullmatch(slug):
        _fail(source, f"{location}.slug", "expected a lowercase kebab-case slug")

    duration = mapping["duration_minutes"]
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        _fail(source, f"{location}.duration_minutes", "expected a positive integer")

    title = _localized_text(
        mapping["title"], source=source, location=f"{location}.title"
    )
    notebook = _localized_paths(
        mapping["notebook"], source=source, location=f"{location}.notebook"
    )
    lecture = _localized_paths(
        mapping["lecture"], source=source, location=f"{location}.lecture"
    )
    stem = f"{lesson_id.lower()}-{slug}"
    for locale in SUPPORTED_LOCALES:
        expected_notebook = PurePosixPath("notebooks") / locale / f"{stem}.ipynb"
        actual_notebook = notebook.for_locale(locale)
        if actual_notebook != expected_notebook:
            _fail(
                source,
                f"{location}.notebook.{locale}",
                f"expected {expected_notebook.as_posix()!r}",
            )
        expected_lecture = PurePosixPath("docs") / locale / "lessons" / f"{stem}.md"
        actual_lecture = lecture.for_locale(locale)
        if actual_lecture != expected_lecture:
            _fail(
                source,
                f"{location}.lecture.{locale}",
                f"expected {expected_lecture.as_posix()!r}",
            )

    return Lesson(
        id=lesson_id,
        slug=slug,
        title=title,
        duration_minutes=duration,
        hardware=_enum_value(
            HardwareRequirement,
            mapping["hardware"],
            source=source,
            location=f"{location}.hardware",
        ),
        notebook=notebook,
        lecture=lecture,
        status=_enum_value(
            CourseStatus,
            mapping["status"],
            source=source,
            location=f"{location}.status",
        ),
    )


def validate_course_manifest(
    data: object,
    *,
    source: str = "<memory>",
) -> CourseManifest:
    """Validate decoded JSON and return an immutable course manifest."""
    root = _object(data, source=source, location="root")
    _keys(root, {"schema_version", "course", "lessons"}, source=source, location="root")

    schema_version = root["schema_version"]
    if schema_version != SCHEMA_VERSION or isinstance(schema_version, bool):
        _fail(source, "schema_version", f"expected integer {SCHEMA_VERSION}")

    course_data = _object(root["course"], source=source, location="course")
    _keys(
        course_data,
        {"id", "title", "default_locale", "locales"},
        source=source,
        location="course",
    )
    course_id = _string(course_data["id"], source=source, location="course.id")
    if not _COURSE_ID_PATTERN.fullmatch(course_id):
        _fail(source, "course.id", "expected a lowercase kebab-case identifier")

    locales = course_data["locales"]
    if locales != list(SUPPORTED_LOCALES):
        _fail(source, "course.locales", f"expected {list(SUPPORTED_LOCALES)!r}")
    default_locale = _string(
        course_data["default_locale"], source=source, location="course.default_locale"
    )
    if default_locale not in SUPPORTED_LOCALES:
        _fail(
            source,
            "course.default_locale",
            f"expected one of {list(SUPPORTED_LOCALES)!r}",
        )

    lessons_data = root["lessons"]
    if not isinstance(lessons_data, list):
        _fail(source, "lessons", "expected an array")
    if len(lessons_data) != LESSON_COUNT:
        _fail(source, "lessons", f"expected exactly {LESSON_COUNT} lessons")

    lessons = tuple(
        _lesson(value, index=index, source=source)
        for index, value in enumerate(lessons_data)
    )
    slugs = [lesson.slug for lesson in lessons]
    if len(slugs) != len(set(slugs)):
        _fail(source, "lessons", "lesson slugs must be unique")

    all_paths = [
        localized_path.for_locale(locale)
        for lesson in lessons
        for localized_path in (lesson.lecture, lesson.notebook)
        for locale in SUPPORTED_LOCALES
    ]
    if len(all_paths) != len(set(all_paths)):
        _fail(source, "lessons", "lecture and notebook paths must be unique")

    return CourseManifest(
        schema_version=schema_version,
        course=CourseInfo(
            id=course_id,
            title=_localized_text(
                course_data["title"], source=source, location="course.title"
            ),
            default_locale=default_locale,
            locales=tuple(locales),
        ),
        lessons=lessons,
    )


def load_course_manifest(path: str | Path | None = None) -> CourseManifest:
    """Load and validate a manifest, defaulting to the configured project root."""
    manifest_path = resolve_cli_path(path, default=DEFAULT_MANIFEST_PATH)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CourseManifestError(
            f"{manifest_path}: cannot read manifest: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CourseManifestError(
            f"{manifest_path}: invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    return validate_course_manifest(data, source=str(manifest_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the RoboGenesis course manifest."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Manifest path (default: <configured project root>/course.json).",
    )
    args = parser.parse_args()
    try:
        manifest = load_course_manifest(args.path)
    except CourseManifestError as exc:
        parser.exit(1, f"course manifest validation failed: {exc}\n")

    status_counts = Counter(lesson.status.value for lesson in manifest.lessons)
    summary = ", ".join(f"{status}={count}" for status, count in status_counts.items())
    print(
        f"Validated {manifest.course.id} schema v{manifest.schema_version}: "
        f"{len(manifest.lessons)} lessons ({summary})"
    )


if __name__ == "__main__":
    main()
