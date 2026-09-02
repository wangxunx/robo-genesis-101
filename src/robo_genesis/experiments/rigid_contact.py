#!/usr/bin/env python3
"""Run one isolated rigid-physics contact case and save structured evidence.

Genesis initialization is process-global, so the rigid-physics notebook launches
this program once per (dt, substeps) configuration instead of asking learners
to restart the notebook kernel between cases.
"""

from __future__ import annotations

import argparse
import importlib.metadata as package_metadata
from collections.abc import Mapping
from pathlib import Path

import numpy as np


from ..course_utils import select_backend, to_numpy


# NOTEBOOK_CONSTANTS_BEGIN
TABLE_CENTER_Z = 0.70
TABLE_HEIGHT = 0.05
TABLE_SIZE = (0.9, 0.6, TABLE_HEIGHT)
TABLE_POSITION = (0.35, 0.0, TABLE_CENTER_Z)
TABLE_FRICTION = 0.8
CUBE_SIZE = 0.08
CUBE_INITIAL_POSITION = (0.35, 0.0, 1.0)
CUBE_DENSITY = 500.0
CUBE_FRICTION = 0.5
EXPECTED_CENTER_Z = TABLE_CENTER_Z + TABLE_HEIGHT / 2 + CUBE_SIZE / 2
# NOTEBOOK_CONSTANTS_END


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--dt", type=float, required=True)
    parser.add_argument("--substeps", type=int, required=True)
    parser.add_argument("--duration", type=float, default=1.5)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


# NOTEBOOK_HELPER_BEGIN
def first_true_index(mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    return int(indices[0]) if indices.size else -1


def validated_step_count(duration: float, dt: float) -> int:
    """Return an exact outer-step count for a positive duration and timestep."""
    if duration <= 0 or dt <= 0:
        raise ValueError("duration and dt must be positive")
    n_steps = round(duration / dt)
    if n_steps < 1 or not np.isclose(n_steps * dt, duration, rtol=0.0, atol=1e-12):
        raise ValueError("duration must be an integer multiple of dt")
    return n_steps


def shared_sample_indices(
    left_time: np.ndarray,
    right_time: np.ndarray,
    *,
    decimals: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    """Return indices for common timestamps in two increasing 1-D timelines."""
    timelines = []
    for name, values in (("left_time", left_time), ("right_time", right_time)):
        timeline = np.asarray(values, dtype=float)
        if timeline.ndim != 1 or timeline.size == 0:
            raise ValueError(f"{name} must be a non-empty 1-D array")
        if not np.isfinite(timeline).all() or np.any(np.diff(timeline) <= 0):
            raise ValueError(f"{name} must contain finite, strictly increasing timestamps")
        timelines.append(np.round(timeline, decimals=decimals))

    _, left_indices, right_indices = np.intersect1d(
        timelines[0], timelines[1], assume_unique=True, return_indices=True
    )
    if left_indices.size == 0:
        raise ValueError("timelines have no common sample timestamps")
    return left_indices, right_indices


def contact_relationship_checks(
    penetrations: Mapping[str, float],
    shared_z_difference: float,
    shared_vz_difference: float,
    *,
    shared_z_tolerance: float,
    shared_vz_tolerance: float,
) -> dict[str, bool]:
    """Evaluate the directional L03 contact relationships without fixed outputs."""
    required = {"N1", "N2", "N3", "N4"}
    if set(penetrations) != required:
        raise ValueError(f"penetrations must contain exactly {sorted(required)}")
    numeric_values = [
        *penetrations.values(),
        shared_z_difference,
        shared_vz_difference,
        shared_z_tolerance,
        shared_vz_tolerance,
    ]
    if not np.isfinite(numeric_values).all() or min(numeric_values) < 0:
        raise ValueError("contact metrics and tolerances must be finite and non-negative")
    return {
        "N1_to_N2_penetration_decreased": penetrations["N2"] < penetrations["N1"],
        "N3_to_N4_penetration_decreased": penetrations["N4"] < penetrations["N3"],
        "N1_N4_shared_z_within_tolerance": shared_z_difference <= shared_z_tolerance,
        "N1_N4_shared_vz_within_tolerance": shared_vz_difference <= shared_vz_tolerance,
    }
# NOTEBOOK_HELPER_END


def main() -> int:
    args = parse_args()
    if args.substeps <= 0:
        raise ValueError("substeps must be positive")

    # NOTEBOOK_CORE_BEGIN
    # NOTEBOOK_SIMULATION_CORE_BEGIN
    n_steps = validated_step_count(args.duration, args.dt)

    import genesis as gs
    import torch

    if args.backend == "cpu":
        backend = gs.cpu
        print("Backend: CPU (explicit request)")
    else:
        backend = select_backend(prefer_rocm=True)
    gs.init(backend=backend, seed=0, precision="32", logging_level="warning")
    if getattr(gs, "amdgpu", None) is not None and gs.backend == gs.amdgpu:
        actual_backend = "amdgpu"
    elif gs.backend == gs.cpu:
        actual_backend = "cpu"
    else:
        actual_backend = str(gs.backend)
    genesis_version = package_metadata.version("genesis-world")
    torch_version = str(torch.__version__)

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=args.dt, substeps=args.substeps),
        rigid_options=gs.options.RigidOptions(enable_collision=True),
        show_viewer=False,
    )
    scene.add_entity(gs.morphs.Plane())
    table = scene.add_entity(
        gs.morphs.Box(size=TABLE_SIZE, pos=TABLE_POSITION, fixed=True),
        material=gs.materials.Rigid(friction=TABLE_FRICTION),
        surface=gs.surfaces.Default(color=(0.55, 0.38, 0.22, 1.0)),
    )
    cube = scene.add_entity(
        gs.morphs.Box(size=(CUBE_SIZE,) * 3, pos=CUBE_INITIAL_POSITION),
        material=gs.materials.Rigid(rho=CUBE_DENSITY, friction=CUBE_FRICTION),
        surface=gs.surfaces.Default(color=(0.15, 0.70, 0.45, 1.0)),
    )
    camera = None
    if args.render:
        camera = scene.add_camera(
            res=(640, 360),
            pos=(1.45, -1.35, 1.25),
            lookat=(0.35, 0.0, 0.78),
            fov=42,
            GUI=False,
        )
    scene.build()
    initial_cube_pos = to_numpy(cube.get_pos()).reshape(-1).copy()

    def render_rgb(label: str) -> np.ndarray:
        if camera is None:
            return np.empty((0,), dtype=np.uint8)
        rgb = to_numpy(camera.render(rgb=True)[0])
        if rgb.ndim != 3 or rgb.shape[0] == 0 or rgb.shape[1] == 0 or rgb.shape[2] not in (3, 4):
            raise AssertionError(f"{label}: expected a non-empty HxWx3/4 image, got {rgb.shape}")
        if not np.isfinite(rgb).all():
            raise AssertionError(f"{label}: image contains non-finite values")
        return rgb.copy()

    initial_rgb = render_rgb("initial_rgb")

    # Record state once after each outer scene.step(). Event times are therefore
    # quantized by dt rather than resolved continuously at substep_dt.
    time_values = np.arange(1, n_steps + 1, dtype=float) * args.dt
    z_history = np.empty(n_steps, dtype=float)
    vz_history = np.empty(n_steps, dtype=float)
    contact_counts = np.empty(n_steps, dtype=int)

    for index in range(n_steps):
        scene.step()
        z_history[index] = float(to_numpy(cube.get_pos()).reshape(-1)[2])
        vz_history[index] = float(to_numpy(cube.get_vel()).reshape(-1)[2])
        contacts = cube.get_contacts(with_entity=table)
        contact_counts[index] = int(contacts["position"].shape[0])
    final_rgb = render_rgb("final_rgb")
    # NOTEBOOK_SIMULATION_CORE_END

    contact_mask = contact_counts > 0
    first_contact_index = first_true_index(contact_mask)
    # The first observed contact time is limited by the outer sampling interval.
    first_contact_time = time_values[first_contact_index] if first_contact_index >= 0 else np.nan
    # Estimate penetration from the lowest recorded center height. This is a
    # trajectory-derived proxy, not an exact solver-internal penetration depth.
    penetration = max(0.0, EXPECTED_CENTER_Z - float(np.min(z_history)))

    if first_contact_index >= 0:
        post_contact_mask = contact_mask[first_contact_index:]
        post_contact_counts = contact_counts[first_contact_index:]
        # Missing contacts alone do not prove that the cube left the table.
        zero_contact_duration = float(np.count_nonzero(~post_contact_mask) * args.dt)
        contact_presence_transitions = int(np.count_nonzero(np.diff(post_contact_mask.astype(int))))
        # Count changes between adjacent observations as a supporting signal
        # for contact-manifold variability, not as a stability verdict.
        contact_count_changes = int(np.count_nonzero(np.diff(post_contact_counts)))
        clearance = z_history[first_contact_index:] - CUBE_SIZE / 2 - (TABLE_CENTER_Z + TABLE_HEIGHT / 2)
        # Require both zero contacts and positive geometric clearance before
        # counting an observation as real separation.
        real_separation_mask = (~post_contact_mask) & (clearance > 1e-5)
        real_separation_duration = float(np.count_nonzero(real_separation_mask) * args.dt)
        max_rebound_clearance = max(0.0, float(np.max(clearance)))
        # Upward motion is not sufficient evidence of rebound without separation.
        max_upward_vz = max(0.0, float(np.max(vz_history[first_contact_index:])))
    else:
        zero_contact_duration = np.nan
        contact_presence_transitions = 0
        contact_count_changes = 0
        real_separation_duration = np.nan
        max_rebound_clearance = np.nan
        max_upward_vz = np.nan

    # Average the final 0.2 s to estimate settling bias. The trajectory is kept
    # because an average alone can hide oscillation.
    tail_start = max(0, n_steps - max(1, round(0.2 / args.dt)))
    settling_error = abs(float(np.mean(z_history[tail_start:])) - EXPECTED_CENTER_Z)
    # NOTEBOOK_CORE_END

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        requested_backend=np.asarray(args.backend),
        actual_backend=np.asarray(actual_backend),
        genesis_version=np.asarray(genesis_version),
        torch_version=np.asarray(torch_version),
        torch_hip=np.asarray(torch.version.hip or "none"),
        render_enabled=np.asarray(args.render),
        seed=np.asarray(0),
        precision=np.asarray("32"),
        dt=np.asarray(args.dt),
        substeps=np.asarray(args.substeps),
        substep_dt=np.asarray(args.dt / args.substeps),
        duration=np.asarray(args.duration),
        n_steps=np.asarray(n_steps),
        table_size=np.asarray(TABLE_SIZE),
        table_position=np.asarray(TABLE_POSITION),
        table_friction=np.asarray(TABLE_FRICTION),
        cube_size=np.asarray(CUBE_SIZE),
        cube_initial_position=np.asarray(CUBE_INITIAL_POSITION),
        cube_density=np.asarray(CUBE_DENSITY),
        cube_friction=np.asarray(CUBE_FRICTION),
        time=time_values,
        z=z_history,
        vz=vz_history,
        contact_count=contact_counts,
        expected_center_z=np.asarray(EXPECTED_CENTER_Z),
        first_contact_time=np.asarray(first_contact_time),
        penetration=np.asarray(penetration),
        zero_contact_duration=np.asarray(zero_contact_duration),
        real_separation_duration=np.asarray(real_separation_duration),
        max_rebound_clearance=np.asarray(max_rebound_clearance),
        max_upward_vz=np.asarray(max_upward_vz),
        contact_presence_transitions=np.asarray(contact_presence_transitions),
        contact_count_changes=np.asarray(contact_count_changes),
        settling_error=np.asarray(settling_error),
        initial_cube_pos=initial_cube_pos,
        final_cube_pos=to_numpy(cube.get_pos()).reshape(-1),
        initial_rgb=initial_rgb,
        final_rgb=final_rgb,
    )
    print(
        f"saved {args.output} | requested={args.backend}, actual={actual_backend}, "
        f"genesis={genesis_version}, torch={torch_version}, "
        f"render={'captured' if args.render else 'disabled'} | "
        f"dt={args.dt:g}, substeps={args.substeps}, "
        f"substep_dt={args.dt / args.substeps:g}, "
        f"penetration={penetration * 1000:.3f} mm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
