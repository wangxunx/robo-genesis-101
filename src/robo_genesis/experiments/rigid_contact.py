#!/usr/bin/env python3
"""Run one isolated rigid-physics contact case and save structured evidence.

Genesis initialization is process-global, so the rigid-physics notebook launches
this program once per (dt, substeps) configuration instead of asking learners
to restart the notebook kernel between cases.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


from ..course_utils import select_backend, to_numpy


# NOTEBOOK_CONSTANTS_BEGIN
TABLE_CENTER_Z = 0.70
TABLE_HEIGHT = 0.05
CUBE_SIZE = 0.08
EXPECTED_CENTER_Z = TABLE_CENTER_Z + TABLE_HEIGHT / 2 + CUBE_SIZE / 2
# NOTEBOOK_CONSTANTS_END


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", type=float, required=True)
    parser.add_argument("--substeps", type=int, required=True)
    parser.add_argument("--duration", type=float, default=1.5)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


# NOTEBOOK_HELPER_BEGIN
def first_true_index(mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    return int(indices[0]) if indices.size else -1
# NOTEBOOK_HELPER_END


def main() -> int:
    args = parse_args()
    if args.dt <= 0 or args.substeps <= 0 or args.duration <= 0:
        raise ValueError("dt, substeps, and duration must be positive")

    # NOTEBOOK_CORE_BEGIN
    n_steps = round(args.duration / args.dt)
    if not np.isclose(n_steps * args.dt, args.duration):
        raise ValueError("duration must be an integer multiple of dt")

    import genesis as gs

    backend = select_backend(prefer_rocm=True)
    gs.init(backend=backend, seed=0, precision="32", logging_level="warning")

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=args.dt, substeps=args.substeps),
        rigid_options=gs.options.RigidOptions(enable_collision=True),
        show_viewer=False,
    )
    scene.add_entity(gs.morphs.Plane())
    table = scene.add_entity(
        gs.morphs.Box(size=(0.9, 0.6, TABLE_HEIGHT), pos=(0.35, 0.0, TABLE_CENTER_Z), fixed=True),
        material=gs.materials.Rigid(friction=0.8),
        surface=gs.surfaces.Default(color=(0.55, 0.38, 0.22, 1.0)),
    )
    cube = scene.add_entity(
        gs.morphs.Box(size=(CUBE_SIZE, CUBE_SIZE, CUBE_SIZE), pos=(0.35, 0.0, 1.0)),
        material=gs.materials.Rigid(rho=500.0, friction=0.5),
        surface=gs.surfaces.Default(color=(0.15, 0.70, 0.45, 1.0)),
    )
    camera = scene.add_camera(
        res=(640, 360),
        pos=(1.45, -1.35, 1.25),
        lookat=(0.35, 0.0, 0.78),
        fov=42,
        GUI=False,
    )
    scene.build()
    initial_cube_pos = to_numpy(cube.get_pos()).reshape(-1).copy()

    initial_rgb = np.empty((0,), dtype=np.uint8)
    final_rgb = np.empty((0,), dtype=np.uint8)
    render_error = ""
    try:
        initial_rgb = to_numpy(camera.render(rgb=True)[0])
    except Exception as exc:  # numerical evidence remains useful without camera output
        render_error = f"{type(exc).__name__}: {exc}"

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

    if not render_error:
        try:
            final_rgb = to_numpy(camera.render(rgb=True)[0])
        except Exception as exc:
            render_error = f"{type(exc).__name__}: {exc}"
            initial_rgb = np.empty((0,), dtype=np.uint8)

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
        dt=np.asarray(args.dt),
        substeps=np.asarray(args.substeps),
        substep_dt=np.asarray(args.dt / args.substeps),
        duration=np.asarray(args.duration),
        n_steps=np.asarray(n_steps),
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
        render_error=np.asarray(render_error),
    )
    print(
        f"saved {args.output} | dt={args.dt:g}, substeps={args.substeps}, "
        f"substep_dt={args.dt / args.substeps:g}, "
        f"penetration={penetration * 1000:.3f} mm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
