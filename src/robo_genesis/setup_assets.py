"""Validate the vendored YCB assets required by the manipulation scene.

RoboGenesis does not copy assets from sibling repositories at runtime. The four
course objects are stored under ``assets/third_party/ycb/models`` with their own
license, provenance, and SHA-256 manifest. The Franka model is provided by the
pinned Genesis installation and is therefore not copied into this repository.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .paths import YCB_ASSET_DIR

YCB_OBJECTS = ("011_banana", "014_lemon", "018_plum", "024_bowl")
REQUIRED_OBJECT_FILES = (
    "collision.ply",
    "material_0.mtl",
    "material_0.png",
    "texture_map.png",
    "textured.mtl",
    "textured.obj",
)
REQUIRED_METADATA_FILES = ("LICENSE-CC-BY-NC-4.0.txt", "README.md", "SHA256SUMS")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_checksums(path: Path) -> dict[Path, str]:
    checksums: dict[Path, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        digest, separator, relative_name = line.partition("  ")
        relative_path = Path(relative_name)
        if (
            not separator
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise ValueError(f"Invalid SHA256SUMS entry at line {line_number}: {raw_line!r}")
        if relative_path in checksums:
            raise ValueError(f"Duplicate SHA256SUMS entry at line {line_number}: {relative_path}")
        checksums[relative_path] = digest
    return checksums


def setup_assets(ycb_asset_dir: Path | None = None) -> Path:
    """Validate the four approved YCB objects and return their models directory."""
    asset_dir = YCB_ASSET_DIR if ycb_asset_dir is None else Path(ycb_asset_dir).resolve()
    models_dir = asset_dir / "models"

    metadata_paths = tuple(asset_dir / name for name in REQUIRED_METADATA_FILES)
    model_paths = tuple(
        models_dir / object_name / file_name
        for object_name in YCB_OBJECTS
        for file_name in REQUIRED_OBJECT_FILES
    )
    missing = [path for path in (*metadata_paths, *model_paths) if not path.is_file()]
    if missing:
        formatted = "\n  ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing required RoboGenesis YCB assets:\n  {formatted}")

    symlinks = [
        path
        for path in (*metadata_paths, *models_dir.rglob("*"))
        if path.is_symlink()
    ]
    if symlinks:
        formatted = "\n  ".join(str(path) for path in symlinks)
        raise ValueError(
            f"Vendored YCB assets must be regular files and directories:\n  {formatted}"
        )

    checksum_path = asset_dir / "SHA256SUMS"
    expected = _read_checksums(checksum_path)
    approved_files = {path.relative_to(asset_dir) for path in model_paths}
    actual_files = {
        path.relative_to(asset_dir)
        for path in models_dir.rglob("*")
        if path.is_file()
    }
    if actual_files != approved_files:
        missing_files = sorted(str(path) for path in approved_files - actual_files)
        unexpected_files = sorted(str(path) for path in actual_files - approved_files)
        raise ValueError(
            "Vendored YCB model files do not match the approved set: "
            f"missing files={missing_files}, unexpected files={unexpected_files}"
        )
    if set(expected) != approved_files:
        missing_entries = sorted(str(path) for path in approved_files - set(expected))
        stale_entries = sorted(str(path) for path in set(expected) - approved_files)
        raise ValueError(
            "SHA256SUMS does not match the approved model file set: "
            f"missing entries={missing_entries}, stale entries={stale_entries}"
        )

    mismatches = [
        str(relative_path)
        for relative_path, expected_digest in expected.items()
        if _sha256(asset_dir / relative_path) != expected_digest
    ]
    if mismatches:
        raise ValueError(f"YCB asset checksum mismatch: {', '.join(sorted(mismatches))}")

    return models_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the vendored YCB assets required by RoboGenesis 101.",
    )
    parser.parse_args()
    models_dir = setup_assets()
    print(f"YCB assets verified at: {models_dir}")
    print("Franka model: Genesis built-in xml/franka_emika_panda/panda.xml")


if __name__ == "__main__":
    main()
