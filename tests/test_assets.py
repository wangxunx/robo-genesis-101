import json
from pathlib import Path

from robo_genesis.setup_assets import REQUIRED_OBJECT_FILES, YCB_OBJECTS, setup_assets

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vendored_ycb_assets_are_complete_and_verified() -> None:
    models_dir = setup_assets()

    assert YCB_OBJECTS == ("011_banana", "014_lemon", "018_plum", "024_bowl")
    assert {path.name for path in models_dir.iterdir() if path.is_dir()} == set(YCB_OBJECTS)
    assert all(
        (models_dir / object_name / file_name).is_file()
        for object_name in YCB_OBJECTS
        for file_name in REQUIRED_OBJECT_FILES
    )
    assert not any(path.is_symlink() for path in models_dir.rglob("*"))


def test_l07_notebooks_expose_the_scene_building_contract() -> None:
    expected_code_ids = (
        "l07-setup",
        "l07-asset-readiness",
        "l07-layout-audit",
        "l07-build-scene",
        "l07-settle-and-measure",
        "l07-camera-observations",
        "l07-banana-candidate",
        "l07-final-check",
    )
    required_code = (
        "setup_assets()",
        "get_ycb_assets(models_dir)",
        "TABLE_TOP_Z + asset.rest_z_offset",
        "asset.radius_xy",
        "combinations(YCB_OBJECTS, 2)",
        "build_scene(",
        "n_envs=1",
        "scene_dr=None",
        "bundle.franka.control_dofs_position(home_qpos)",
        "bundle.scene.step()",
        "bundle.update_wrist_cam()",
        "entity.get_AABB()",
        "bundle.render(rgb=True, depth=True)",
        "L07 CHECK: PASSED",
    )

    for locale in ("en", "zh"):
        path = (
            PROJECT_ROOT
            / "notebooks"
            / locale
            / "l07-building-a-grasping-task-scene.ipynb"
        )
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = notebook["cells"]
        code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
        code_source = "\n".join("".join(cell["source"]) for cell in code_cells)

        assert len(cells) == 17
        assert tuple(cell["id"] for cell in code_cells) == expected_code_ids
        assert notebook["metadata"]["robo_genesis"]["duration_minutes"] == 90
        assert notebook["metadata"]["robo_genesis"]["status"] == "planned"
        assert all(cell["execution_count"] is None for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)
        assert all(fragment in code_source for fragment in required_code)
        assert "add_video_cam=False" in code_source
