import json
import re
import textwrap
from pathlib import Path

import numpy as np
import pytest

from robo_genesis.experiments.rigid_contact import (
    contact_relationship_checks,
    first_true_index,
    shared_sample_indices,
    validated_step_count as contact_step_count,
)
from robo_genesis.experiments.rigid_friction import (
    effective_pair_friction,
    friction_relationship_checks,
    sustained_stop_index,
    validated_step_count as friction_step_count,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _marked_source(path: Path, start_marker: str, end_marker: str) -> str:
    source = path.read_text(encoding="utf-8")
    marked = source.split(start_marker, 1)[1].split(end_marker, 1)[0]
    return textwrap.dedent(marked).strip()


def _python_fence(markdown: str) -> str:
    match = re.search(r"```python\n(.*?)\n```", markdown, flags=re.DOTALL)
    if match is None:
        raise AssertionError("expected one fenced Python block")
    return match.group(1).strip()


def test_contact_time_grid_requires_an_exact_positive_step_count() -> None:
    assert contact_step_count(1.5, 0.01) == 150
    assert contact_step_count(1.5, 0.02) == 75

    with pytest.raises(ValueError, match="positive"):
        contact_step_count(1.5, 0.0)
    with pytest.raises(ValueError, match="integer multiple"):
        contact_step_count(1.0, 0.3)


def test_shared_sample_indices_align_different_outer_timesteps() -> None:
    n1_time = np.arange(1, 151, dtype=float) * 0.01
    n4_time = np.arange(1, 76, dtype=float) * 0.02

    n1_indices, n4_indices = shared_sample_indices(n1_time, n4_time)

    assert n1_indices.shape == n4_indices.shape == (75,)
    np.testing.assert_allclose(n1_time[n1_indices], n4_time[n4_indices])
    np.testing.assert_array_equal(n1_indices[:3], np.array([1, 3, 5]))
    np.testing.assert_array_equal(n4_indices[:3], np.array([0, 1, 2]))


def test_shared_sample_indices_reject_invalid_or_disjoint_timelines() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        shared_sample_indices(np.array([0.1, 0.1]), np.array([0.1]))
    with pytest.raises(ValueError, match="no common"):
        shared_sample_indices(np.array([0.1, 0.2]), np.array([0.15, 0.25]))


def test_first_true_index_reports_missing_events() -> None:
    assert first_true_index(np.array([False, False, True, True])) == 2
    assert first_true_index(np.array([False, False])) == -1


def test_sustained_stop_rejects_a_single_low_speed_crossing() -> None:
    speed = np.array([0.3, 0.005, 0.2, 0.009, 0.008, 0.007, 0.006])

    assert sustained_stop_index(speed, threshold=0.01, hold_samples=3) == 3
    assert sustained_stop_index(speed, threshold=0.001, hold_samples=2) == -1

    with pytest.raises(ValueError, match="hold_samples"):
        sustained_stop_index(speed, threshold=0.01, hold_samples=0)
    with pytest.raises(ValueError, match="finite"):
        sustained_stop_index(np.array([0.1, np.nan]), threshold=0.01, hold_samples=1)


def test_friction_time_grid_and_effective_pair_rule() -> None:
    assert friction_step_count(0.3, 0.01, label="settle-duration") == 30
    assert friction_step_count(2.0, 0.01, label="measure-duration") == 200
    assert effective_pair_friction(0.50, 0.10) == 0.50
    assert effective_pair_friction(0.50, 0.80) == 0.80
    assert effective_pair_friction(0.30, 0.10) == 0.30
    assert effective_pair_friction(0.30, 0.80) == 0.80

    with pytest.raises(ValueError, match="integer multiple"):
        friction_step_count(1.0, 0.3, label="measure-duration")
    with pytest.raises(ValueError, match="non-negative"):
        effective_pair_friction(-0.1, 0.5)


def test_contact_relationships_use_directions_and_declared_tolerances() -> None:
    checks = contact_relationship_checks(
        {"N1": 0.013, "N2": 0.008, "N3": 0.024, "N4": 0.013},
        shared_z_difference=2e-6,
        shared_vz_difference=3e-5,
        shared_z_tolerance=1e-5,
        shared_vz_tolerance=1e-4,
    )

    assert all(checks.values())
    assert not contact_relationship_checks(
        {"N1": 0.013, "N2": 0.014, "N3": 0.024, "N4": 0.013},
        shared_z_difference=2e-6,
        shared_vz_difference=3e-5,
        shared_z_tolerance=1e-5,
        shared_vz_tolerance=1e-4,
    )["N1_to_N2_penetration_decreased"]


def test_friction_relationships_check_both_changed_and_control_lanes() -> None:
    checks = friction_relationship_checks(
        baseline_low_distance=0.41,
        baseline_high_distance=0.224,
        modified_low_distance=0.675,
        modified_high_distance=0.2245,
        unchanged_tolerance=1e-3,
    )

    assert all(checks.values())
    assert not friction_relationship_checks(
        baseline_low_distance=0.41,
        baseline_high_distance=0.224,
        modified_low_distance=0.675,
        modified_high_distance=0.230,
        unchanged_tolerance=1e-3,
    )["high_lane_approximately_unchanged"]


def test_l03_notebooks_keep_the_lesson_title_and_expose_key_logic() -> None:
    expected_titles = {
        "en": "# L03 · Rigid-Body Physics and Stable Simulation",
        "zh": "# L03 · 刚体物理与稳定仿真",
    }
    gpu_first_text = {
        "en": "GPU is the preferred backend for this course.",
        "zh": "GPU 是本课程的首选后端。",
    }
    exposed_definitions = (
        "def validated_step_count(",
        "def contact_metrics_from_samples(",
        "def shared_sample_indices(",
        "def effective_pair_friction(",
        "def sustained_stop_index(",
        "def stop_measurement(",
        "def format_distance(",
    )
    guided_interpretation_sections = (
        "### Guided interpretation",
        "**1. Hold `dt` fixed and change `substeps`.**",
        "**2. Match `substep_dt` and change the external step boundary.**",
        "**3. Scope the conclusion.**",
        "**4. Do not infer rebound from contact count alone.**",
    )
    guided_friction_sections = (
        "### Guided friction interpretation",
        "**1. Read the controlled comparison.**",
        "**2. Interpret sustained stopping, not one low-speed sample.**",
        "**3. Keep rotation and contact in the evidence chain.**",
        "**4. Bound the conclusion.**",
        "### Guided one-factor interpretation",
        "**1. Verify the intervention.**",
        "**2. Follow the effective pair values.**",
        "**3. Compare measured stopping distances.**",
        "**4. State only what this one-factor experiment supports.**",
    )
    contact_runner_core = _marked_source(
        PROJECT_ROOT / "src" / "robo_genesis" / "experiments" / "rigid_contact.py",
        "# NOTEBOOK_SIMULATION_CORE_BEGIN",
        "# NOTEBOOK_SIMULATION_CORE_END",
    )
    friction_runner_core = _marked_source(
        PROJECT_ROOT / "src" / "robo_genesis" / "experiments" / "rigid_friction.py",
        "# NOTEBOOK_SIMULATION_CORE_BEGIN",
        "# NOTEBOOK_SIMULATION_CORE_END",
    )

    for locale in ("en", "zh"):
        path = (
            PROJECT_ROOT
            / "notebooks"
            / locale
            / "l03-rigid-body-physics-and-stable-simulation.ipynb"
        )
        notebook = json.loads(path.read_text(encoding="utf-8"))
        first_markdown = next(
            cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"
        )
        markdown_source = "".join(
            line
            for cell in notebook["cells"]
            if cell["cell_type"] == "markdown"
            for line in cell["source"]
        )
        code_source = "".join(
            line
            for cell in notebook["cells"]
            if cell["cell_type"] == "code"
            for line in cell["source"]
        )
        cell_ids = [cell["id"] for cell in notebook["cells"]]
        contact_core_cells = [
            cell for cell in notebook["cells"] if cell["id"] == "l03-part-a-core"
        ]
        friction_core_cells = [
            cell for cell in notebook["cells"] if cell["id"] == "l03-part-b-core"
        ]

        assert "".join(first_markdown["source"]).splitlines()[0] == expected_titles[locale]
        assert gpu_first_text[locale] in markdown_source
        assert len(contact_core_cells) == 1
        assert cell_ids.index("l03-part-a-core") < cell_ids.index("l03-part-a-run")
        assert _python_fence("".join(contact_core_cells[0]["source"])) == contact_runner_core
        assert len(friction_core_cells) == 1
        assert cell_ids.index("l03-part-b-core") < cell_ids.index("l03-part-b-run")
        assert _python_fence("".join(friction_core_cells[0]["source"])) == friction_runner_core
        assert "### Evidence-based interpretation" not in code_source
        for section in guided_interpretation_sections:
            assert section in code_source
        for section in guided_friction_sections:
            assert section in code_source
        for runtime_evidence in (
            "first_contact_time",
            "real_separation_duration",
            "zero_contact_duration",
            "max_rebound_clearance",
            "max_upward_vz",
            "contact_count_changes",
            "settling_error",
            "baseline_stop_measurements",
            "max_abs_omega_low",
            "contact_fraction_low",
            "modified_stop_measurements",
            "part_b_checks",
            "HIGH_LANE_UNCHANGED_TOLERANCE",
        ):
            assert runtime_evidence in code_source
        assert "from robo_genesis.experiments" not in code_source
        assert "import robo_genesis.experiments" not in code_source
        assert "from robo_genesis.course_utils import notebook_mode" in code_source
        for definition in exposed_definitions:
            assert definition in code_source
