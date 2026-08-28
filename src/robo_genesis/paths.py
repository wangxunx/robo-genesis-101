"""Central path configuration for RoboGenesis 101.

The default layout is rooted at the current repository checkout. Installed
copies that are run elsewhere default to the current working directory. Set
``ROBO_GENESIS_ROOT`` to choose an explicit workspace, or override the assets,
datasets, and outputs directories individually. Relative override values are
resolved against the configured project root.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT_ENV = "ROBO_GENESIS_ROOT"
ASSETS_ENV = "ROBO_GENESIS_ASSETS_DIR"
DATASETS_ENV = "ROBO_GENESIS_DATASETS_DIR"
OUTPUTS_ENV = "ROBO_GENESIS_OUTPUTS_DIR"


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved input and output directories for one course workspace."""

    project_root: Path
    assets_dir: Path
    datasets_dir: Path
    outputs_dir: Path

    @property
    def ycb_asset_dir(self) -> Path:
        return self.assets_dir / "third_party" / "ycb"

    @property
    def ycb_models_dir(self) -> Path:
        return self.ycb_asset_dir / "models"

    @property
    def train_outputs_dir(self) -> Path:
        return self.outputs_dir / "train"

    @property
    def eval_results_dir(self) -> Path:
        return self.outputs_dir / "eval_results"

    @property
    def eval_videos_dir(self) -> Path:
        return self.outputs_dir / "eval_videos"

    @property
    def frames_dir(self) -> Path:
        return self.outputs_dir / "grasp_demo_frames"

    @property
    def scene_frames_dir(self) -> Path:
        return self.outputs_dir / "scene_frames"


def _absolute_path(value: str | Path, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _checkout_root(package_file: Path) -> Path | None:
    """Find a source checkout without assuming a fixed number of parents."""
    for candidate in package_file.resolve().parents:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src" / "robo_genesis"
        ).is_dir():
            return candidate
    return None


def resolve_project_paths(
    environ: Mapping[str, str] | None = None,
    *,
    cwd: Path | None = None,
    package_file: Path | None = None,
) -> ProjectPaths:
    """Resolve course paths from environment variables and portable defaults."""
    environment = os.environ if environ is None else environ
    current_dir = (Path.cwd() if cwd is None else cwd).expanduser().resolve()
    module_file = Path(__file__) if package_file is None else package_file

    configured_root = environment.get(ROOT_ENV)
    if configured_root:
        project_root = _absolute_path(configured_root, base=current_dir)
    else:
        project_root = _checkout_root(module_file) or current_dir

    def configured_dir(variable: str, default_name: str) -> Path:
        value = environment.get(variable)
        return _absolute_path(value or default_name, base=project_root)

    return ProjectPaths(
        project_root=project_root,
        assets_dir=configured_dir(ASSETS_ENV, "assets"),
        datasets_dir=configured_dir(DATASETS_ENV, "datasets"),
        outputs_dir=configured_dir(OUTPUTS_ENV, "outputs"),
    )


def resolve_cli_path(value: str | Path | None, *, default: Path | None = None) -> Path:
    """Resolve an explicit CLI path from the CWD, or return an absolute default."""
    if value is None:
        if default is None:
            raise ValueError("A path value or default is required.")
        return default.resolve()
    return _absolute_path(value, base=Path.cwd().resolve())


PATHS = resolve_project_paths()

PROJECT_ROOT = PATHS.project_root
ASSETS_DIR = PATHS.assets_dir
YCB_ASSET_DIR = PATHS.ycb_asset_dir
YCB_MODELS_DIR = PATHS.ycb_models_dir
DATASETS_DIR = PATHS.datasets_dir
OUTPUTS_DIR = PATHS.outputs_dir
TRAIN_OUTPUTS_DIR = PATHS.train_outputs_dir
EVAL_RESULTS_DIR = PATHS.eval_results_dir
EVAL_VIDEOS_DIR = PATHS.eval_videos_dir
FRAMES_DIR = PATHS.frames_dir
SCENE_FRAMES_DIR = PATHS.scene_frames_dir

__all__ = [
    "ASSETS_DIR",
    "ASSETS_ENV",
    "DATASETS_DIR",
    "DATASETS_ENV",
    "EVAL_RESULTS_DIR",
    "EVAL_VIDEOS_DIR",
    "FRAMES_DIR",
    "OUTPUTS_DIR",
    "OUTPUTS_ENV",
    "PATHS",
    "PROJECT_ROOT",
    "ProjectPaths",
    "ROOT_ENV",
    "SCENE_FRAMES_DIR",
    "TRAIN_OUTPUTS_DIR",
    "YCB_ASSET_DIR",
    "YCB_MODELS_DIR",
    "resolve_cli_path",
    "resolve_project_paths",
]
