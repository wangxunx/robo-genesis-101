import json
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_episode_recorder_keeps_its_fractional_accumulator() -> None:
    source = (PROJECT_ROOT / "src" / "robo_genesis" / "record_dataset.py").read_text(
        encoding="utf-8"
    )

    expected_fragments = (
        "self.steps_per_frame = control_fps / fps",
        "self._accum = self.steps_per_frame",
        "self._accum += 1.0",
        "if self._accum < self.steps_per_frame:",
        "self._accum -= self.steps_per_frame",
    )
    assert all(fragment in source for fragment in expected_fragments)
    assert "FractionalSamplingClock" not in source


def test_data_extra_installs_the_lerobot_dataset_api() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "lerobot[dataset]==0.6.0" in pyproject["project"]["optional-dependencies"]["data"]


def test_l09_notebooks_expose_the_recording_contract() -> None:
    expected_code_ids = (
        "l09-setup",
        "l09-sampling-contract",
        "l09-feature-contract",
        "l09-runtime-setup",
        "l09-record-episodes",
        "l09-readback",
        "l09-visual-evidence",
        "l09-final-check",
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
        "code",
        "markdown",
    )
    required_code = (
        "os.environ.get('ROBO_GENESIS_RENDER', '1')",
        "RG101_L09_OVERWRITE",
        "dataset_root.name != 'l09_banana_demo'",
        "steps_per_frame = CONTROL_FPS / dataset_fps",
        "accum = steps_per_frame",
        "accum += 1.0",
        "if accum < steps_per_frame:",
        "accum -= steps_per_frame",
        "CANDIDATE_DATASET_FPS",
        "build_features(IMG_WH)",
        "tuple(JOINT_NAMES)",
        "LeRobotDataset.create(",
        "RGBEncoderConfig(vcodec='h264', video_backend='pyav')",
        "n_envs=1",
        "add_world_cam=True",
        "add_wrist_cam=True",
        "recorder.reset()",
        "run_pick_place(bundle, task, recorder=recorder)",
        "if success and len(recorder) > 0:",
        "recorder.flush_to(dataset, task_text)",
        "dataset.finalize()",
        "LeRobotDatasetMetadata(REPO_ID, root=dataset_root)",
        "video_backend='pyav'",
        "plain_rows = rows.with_format(None)",
        "np.asarray(plain_rows['index'], dtype=np.int64)",
        "np.asarray(plain_rows['observation.state'], dtype=float)",
        "frame_indices[episode_indices == episode] / DATASET_FPS",
        "lesson.status.value == 'gpu-verified'",
        "observation.images.world",
        "observation.images.wrist",
        "L09 CHECK: PASSED",
        "L09 DIAGNOSTIC CHECK: PASSED",
        "Core recording experiment: NOT COMPLETED",
    )
    forbidden_code = (
        "sys.path",
        "FAILED:",
        "n_envs=4",
        "np.zeros((height, width, 3))",
        "robo_genesis.recording_contract",
        "capture_schedule",
        "recorder.capture_steps",
        "recorder.control_steps",
        "lesson.status.value == 'planned'",
    )
    localized_code: dict[str, tuple[str, ...]] = {}

    for locale in ("en", "zh"):
        path = (
            PROJECT_ROOT
            / "notebooks"
            / locale
            / "l09-synthetic-data-recording-and-throughput.ipynb"
        )
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = notebook["cells"]
        code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
        code_sources = tuple("".join(cell["source"]) for cell in code_cells)
        code_source = "\n".join(code_sources)
        localized_code[locale] = code_sources

        assert len(cells) == 18
        assert tuple(cell["cell_type"] for cell in cells) == expected_cell_types
        assert tuple(cell["id"] for cell in code_cells) == expected_code_ids
        assert notebook["metadata"]["robo_genesis"] == {
            "lesson": "L09",
            "slug": "synthetic-data-recording-and-throughput",
            "locale": locale,
            "duration_minutes": 120,
            "hardware": "gpu-recommended",
            "status": "gpu-verified",
        }
        assert all(cell["execution_count"] is None for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)
        assert all(fragment in code_source for fragment in required_code)
        assert all(fragment not in code_source for fragment in forbidden_code)

        sampling_source = next(cell for cell in code_cells if cell["id"] == "l09-sampling-contract")
        namespace = {"CONTROL_FPS": 100, "DATASET_FPS": 5}
        exec("".join(sampling_source["source"]), namespace)
        assert namespace["five_fps_schedule"]["indices"] == (0, 19, 39, 59, 79, 99)
        assert namespace["thirty_fps_schedule"]["indices"][:5] == (0, 3, 6, 10, 13)

        markdown_source = "\n".join(
            "".join(cell["source"])
            for cell in cells
            if cell["cell_type"] == "markdown"
        )
        diagram_suffix = "-zh" if locale == "zh" else ""
        assert f"l09-alignment-and-episode-transaction{diagram_suffix}.svg" in markdown_source

    assert localized_code["en"] == localized_code["zh"]
