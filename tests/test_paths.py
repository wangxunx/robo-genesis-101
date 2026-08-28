from pathlib import Path

from robo_genesis.paths import (
    ASSETS_DIR,
    DATASETS_DIR,
    OUTPUTS_DIR,
    PROJECT_ROOT,
    SCENE_FRAMES_DIR,
    resolve_cli_path,
    resolve_project_paths,
)


def test_checkout_defaults_point_at_repository_root() -> None:
    expected_root = Path(__file__).resolve().parents[1]

    assert PROJECT_ROOT == expected_root
    assert ASSETS_DIR == expected_root / "assets"
    assert DATASETS_DIR == expected_root / "datasets"
    assert OUTPUTS_DIR == expected_root / "outputs"
    assert SCENE_FRAMES_DIR == expected_root / "outputs" / "scene_frames"


def test_environment_overrides_resolve_from_configured_root(tmp_path: Path) -> None:
    current_dir = tmp_path / "current"
    current_dir.mkdir()
    external_datasets = tmp_path / "external-datasets"
    paths = resolve_project_paths(
        {
            "ROBO_GENESIS_ROOT": "workspace",
            "ROBO_GENESIS_ASSETS_DIR": "shared-assets",
            "ROBO_GENESIS_DATASETS_DIR": str(external_datasets),
            "ROBO_GENESIS_OUTPUTS_DIR": "artifacts",
        },
        cwd=current_dir,
        package_file=tmp_path / "installed" / "robo_genesis" / "paths.py",
    )

    assert paths.project_root == current_dir / "workspace"
    assert paths.assets_dir == current_dir / "workspace" / "shared-assets"
    assert paths.datasets_dir == external_datasets
    assert paths.outputs_dir == current_dir / "workspace" / "artifacts"


def test_cli_paths_are_relative_to_working_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert resolve_cli_path("runs/example") == tmp_path / "runs" / "example"
