import ast
import json
import math
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_NAME = "l10-dataset-anatomy-and-imitation-learning.ipynb"


def _load_notebook(locale: str) -> dict:
    path = PROJECT_ROOT / "notebooks" / locale / NOTEBOOK_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def test_l10_notebooks_expose_the_dataset_read_contract() -> None:
    expected_code_ids = (
        "l10-setup",
        "l10-metadata-contract",
        "l10-sample-readback",
        "l10-statistics",
        "l10-split-protocol",
        "l10-action-chunk",
        "l10-policy-contracts",
        "l10-final-check",
    )
    expected_cell_types = ("markdown", "markdown") + tuple(
        cell_type for _ in range(8) for cell_type in ("code", "markdown")
    )
    required_code = (
        "os.environ.get('RG101_L10_DATASET_ROOT')",
        "(DATASETS_DIR / 'l09_banana_demo').resolve()",
        "RG101_L10_REPO_ID",
        "HF_DATASETS_CACHE",
        "meta' / 'info.json",
        "meta' / 'stats.json",
        "meta' / 'tasks.parquet",
        "No download or fallback dataset is attempted",
        "LeRobotDatasetMetadata(REPO_ID, root=dataset_root)",
        "metadata.get_data_file_path",
        "metadata.get_video_file_path",
        "video.codec",
        "dataset_from_index",
        "dataset_to_index",
        "tuple(JOINT_NAMES)",
        "LeRobotDataset(REPO_ID, root=dataset_root, video_backend='pyav')",
        "dataset.hf_dataset.with_format(None)",
        "plt.subplots(2, 3",
        "required_stat_names",
        "(3, 1, 1)",
        "arm_scale = max(arm_std, epsilon)",
        "def plan_episode_split(records, eval_split=0.2):",
        "math.ceil(len(episode_ids) * eval_split)",
        "set(train_episode_ids).isdisjoint(eval_episode_ids)",
        "MECHANICS ONLY: two episodes do not form a stable benchmark",
        "'action': [i / fps for i in range(H)]",
        "action_is_pad",
        "nominal_horizon_s = H / fps",
        "final_target_offset_s = (H - 1) / fps",
        "from robo_genesis.train_policy import PRESETS",
        "expected_smolvla_rename",
        "No model was imported or allocated",
        "Training: NOT RUN",
        "Checkpoint: NOT CREATED",
        "Genesis rollout: NOT RUN",
        "Task success rate: NOT MEASURED",
        "L10 CHECK: PASSED",
    )
    forbidden_code = (
        "sys.path",
        "import genesis",
        "gs.init",
        "LeRobotDataset.create",
        "snapshot_download",
        "hf_hub_download",
        "force_cache_sync=True",
        "save_episode(",
        "finalize()",
        "shutil.rmtree",
        "lerobot_train",
        "torch.cuda",
        "from transformers",
        "lesson.status.value == 'gpu-verified'",
        "metadata.total_frames == 85",
        "libsvtav1",
        "raw_first",
        "raw_decoded_numeric_match",
        "Raw state row",
        "Decoded action:",
        "print(f'L10: {lesson.duration_minutes}",
    )
    localized_code: dict[str, tuple[str, ...]] = {}

    for locale in ("en", "zh"):
        notebook = _load_notebook(locale)
        cells = notebook["cells"]
        code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
        code_sources = tuple("".join(cell["source"]) for cell in code_cells)
        code_source = "\n".join(code_sources)
        localized_code[locale] = code_sources

        assert len(cells) == 18
        assert tuple(cell["cell_type"] for cell in cells) == expected_cell_types
        assert tuple(cell["id"] for cell in code_cells) == expected_code_ids
        assert notebook["metadata"]["robo_genesis"] == {
            "lesson": "L10",
            "slug": "dataset-anatomy-and-imitation-learning",
            "locale": locale,
            "duration_minutes": 90,
            "hardware": "gpu-recommended",
            "status": "planned",
        }
        assert all(cell["execution_count"] is None for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)
        assert all(fragment in code_source for fragment in required_code)
        assert all(fragment not in code_source for fragment in forbidden_code)
        for source in code_sources:
            compile(source, f"{locale}/{NOTEBOOK_NAME}", "exec")

        setup_source = code_sources[0]
        assert "lerobot.datasets" not in setup_source
        assert "robo_genesis.record_dataset" not in setup_source
        markdown_source = "\n".join(
            "".join(cell["source"])
            for cell in cells
            if cell["cell_type"] == "markdown"
        )
        assert "M3.L10" not in markdown_source
        assert "not been published" not in markdown_source
        before_run = next(cell for cell in cells if cell["id"] == "l10-before-run")
        assert before_run["cell_type"] == "markdown"
        sample_heading = (
            "## Read and assemble a multimodal training sample"
            if locale == "en"
            else "## 从数据集读取并组装多模态训练 sample"
        )
        assert sample_heading in markdown_source

    assert localized_code["en"] == localized_code["zh"]


def test_l10_notebook_episode_split_matches_the_pinned_factory_rule() -> None:
    notebook = _load_notebook("en")
    split_cell = next(cell for cell in notebook["cells"] if cell["id"] == "l10-split-protocol")
    module = ast.parse("".join(split_cell["source"]))
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "plan_episode_split"
    )
    namespace = {"math": math}
    exec(compile(ast.Module(body=[function], type_ignores=[]), NOTEBOOK_NAME, "exec"), namespace)

    records = [
        {"episode_index": 0, "tasks": ("pick",)},
        {"episode_index": 1, "tasks": ("pick",)},
        {"episode_index": 2, "tasks": ("pick",)},
        {"episode_index": 3, "tasks": ("place",)},
        {"episode_index": 4, "tasks": ("place",)},
    ]
    train_ids, eval_ids = namespace["plan_episode_split"](records, eval_split=0.2)

    assert train_ids == [0, 1, 3]
    assert eval_ids == [2, 4]
    assert set(train_ids).isdisjoint(eval_ids)
    assert set(train_ids) | set(eval_ids) == {0, 1, 2, 3, 4}

    with pytest.raises(ValueError, match="no training episodes"):
        namespace["plan_episode_split"](
            [
                {"episode_index": 0, "tasks": ("pick",)},
                {"episode_index": 1, "tasks": ("place",)},
            ],
            eval_split=0.2,
        )
