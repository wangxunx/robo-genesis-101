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
        assert notebook["metadata"]["robo_genesis"]["status"] == "cpu-verified"
        assert all(cell["execution_count"] is None for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)
        assert all(fragment in code_source for fragment in required_code)
        assert "add_video_cam=False" in code_source


def test_l08_notebooks_expose_the_scripted_expert_contract() -> None:
    expected_code_ids = (
        "l08-setup",
        "l08-expert-contract",
        "l08-rate-schedule",
        "l08-build-scene",
        "l08-rollout",
        "l08-evidence",
        "l08-final-check",
    )
    expected_cell_types = (
        "markdown",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
        "code",
        "markdown",
    )
    required_code = (
        "TaskSpec(",
        "isinstance(profile, GraspProfile)",
        "tuple(row[0] for row in PHASES)",
        "os.environ.get('ROBO_GENESIS_RENDER', '1')",
        "np.ceil(delta_q_inf / MOVE_MAX_DQ)",
        "CANDIDATE_MAX_DQ",
        "make_command_schedule(",
        "build_scene(",
        "add_world_cam=render_enabled",
        "add_wrist_cam=False",
        "add_video_cam=False",
        "scene_dr=None",
        "class TraceRecorder:",
        "self.bundle.franka.get_qpos()",
        "run_pick_place(",
        "save_frames=render_enabled",
        "state_trace = np.stack(trace.states)",
        "action_trace = np.stack(trace.actions)",
        "within_footprint",
        "inside_bowl",
        "check_success(bundle, task)",
        "EXPECTED_FRAME_TAGS",
        "tracking_joint",
        "allowed_circle = plt.Circle(",
        "L08 CHECK: PASSED",
    )
    forbidden_code = (
        "LeRobotDataset",
        "record_dataset",
        "SceneDomainRandomizationConfig",
        "apply_episode_randomization",
        "sys.path",
    )
    localized_code: dict[str, tuple[str, ...]] = {}

    for locale in ("en", "zh"):
        path = (
            PROJECT_ROOT
            / "notebooks"
            / locale
            / "l08-demonstration-acquisition-and-scripted-experts.ipynb"
        )
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = notebook["cells"]
        code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
        code_sources = tuple("".join(cell["source"]) for cell in code_cells)
        code_source = "\n".join(code_sources)
        localized_code[locale] = code_sources

        assert len(cells) == 16
        assert tuple(cell["cell_type"] for cell in cells) == expected_cell_types
        assert tuple(cell["id"] for cell in code_cells) == expected_code_ids
        assert notebook["metadata"]["robo_genesis"] == {
            "lesson": "L08",
            "slug": "demonstration-acquisition-and-scripted-experts",
            "locale": locale,
            "duration_minutes": 120,
            "hardware": "gpu-recommended",
            "status": "gpu-verified",
        }
        assert all(cell["execution_count"] is None for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)
        assert all(fragment in code_source for fragment in required_code)
        assert all(fragment not in code_source for fragment in forbidden_code)
        assert "os.environ.get('ROBO_GENESIS_RENDER', '0')" not in code_source
        assert code_source.count("PASS") == 1
        markdown_source = "\n".join(
            "".join(cell["source"])
            for cell in cells
            if cell["cell_type"] == "markdown"
        )
        assert f"l08-seven-phase-pick-place{'-zh' if locale == 'zh' else ''}.svg" in markdown_source

    assert localized_code["en"] == localized_code["zh"]


def test_l08_and_later_render_switches_default_to_enabled() -> None:
    notebooks_with_render_switch: set[str] = set()
    enabled_defaults = (
        "get('ROBO_GENESIS_RENDER', '1')",
        'get("ROBO_GENESIS_RENDER", "1")',
    )
    disabled_defaults = (
        "get('ROBO_GENESIS_RENDER', '0')",
        'get("ROBO_GENESIS_RENDER", "0")',
    )

    for locale in ("en", "zh"):
        for path in sorted((PROJECT_ROOT / "notebooks" / locale).glob("l*.ipynb")):
            lesson_number = int(path.name[1:3])
            if lesson_number < 8:
                continue
            notebook = json.loads(path.read_text(encoding="utf-8"))
            code_source = "\n".join(
                "".join(cell["source"])
                for cell in notebook["cells"]
                if cell["cell_type"] == "code"
            )
            if "ROBO_GENESIS_RENDER" not in code_source:
                continue
            notebooks_with_render_switch.add(path.as_posix())
            assert any(fragment in code_source for fragment in enabled_defaults)
            assert all(fragment not in code_source for fragment in disabled_defaults)

    assert {
        str(
            PROJECT_ROOT
            / "notebooks"
            / locale
            / "l08-demonstration-acquisition-and-scripted-experts.ipynb"
        )
        for locale in ("en", "zh")
    }.issubset(notebooks_with_render_switch)
