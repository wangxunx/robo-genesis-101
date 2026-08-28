#!/usr/bin/env python3
"""Run the isolated rigid-physics sliding-friction comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


from ..course_utils import select_backend, to_numpy


# NOTEBOOK_CONSTANTS_BEGIN
TABLE_CENTER_Z = 0.70
TABLE_HEIGHT = 0.05
CUBE_SIZE = 0.08
RESTING_CENTER_Z = TABLE_CENTER_Z + TABLE_HEIGHT / 2 + CUBE_SIZE / 2
LOW_LANE_Y = -0.15
HIGH_LANE_Y = 0.15
START_X = -0.60
# NOTEBOOK_CONSTANTS_END


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--substeps", type=int, default=2)
    parser.add_argument("--settle-duration", type=float, default=0.30)
    parser.add_argument("--measure-duration", type=float, default=2.00)
    parser.add_argument("--initial-vx", type=float, default=2.00)
    parser.add_argument("--table-friction", type=float, default=0.50)
    parser.add_argument("--low-friction", type=float, default=0.10)
    parser.add_argument("--high-friction", type=float, default=0.80)
    parser.add_argument("--stop-speed", type=float, default=0.01)
    parser.add_argument("--stop-hold", type=float, default=0.10)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


# NOTEBOOK_HELPER_BEGIN
def sustained_stop_index(speed: np.ndarray, threshold: float, hold_samples: int) -> int:
    """Return the first sample starting a sustained below-threshold interval."""
    below = np.abs(speed) < threshold
    for index in range(0, len(speed) - hold_samples + 1):
        if np.all(below[index : index + hold_samples]):
            return index
    return -1
# NOTEBOOK_HELPER_END


def main() -> int:
    args = parse_args()
    positive = (args.dt, args.substeps, args.settle_duration, args.measure_duration, args.initial_vx)
    if any(value <= 0 for value in positive):
        raise ValueError("dt, substeps, durations, and initial_vx must be positive")
    if min(args.table_friction, args.low_friction, args.high_friction, args.stop_speed, args.stop_hold) < 0:
        raise ValueError("friction and stopping thresholds must be non-negative")

    # NOTEBOOK_CORE_BEGIN
    settle_steps = round(args.settle_duration / args.dt)
    measure_steps = round(args.measure_duration / args.dt)
    hold_samples = max(1, round(args.stop_hold / args.dt))
    if not np.isclose(settle_steps * args.dt, args.settle_duration):
        raise ValueError("settle-duration must be an integer multiple of dt")
    if not np.isclose(measure_steps * args.dt, args.measure_duration):
        raise ValueError("measure-duration must be an integer multiple of dt")

    import genesis as gs

    backend = select_backend(prefer_rocm=True)
    gs.init(backend=backend, seed=0, precision="32", logging_level="warning")

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=args.dt, substeps=args.substeps),
        rigid_options=gs.options.RigidOptions(enable_collision=True),
        show_viewer=False,
    )
    table = scene.add_entity(
        gs.morphs.Box(size=(2.0, 0.8, TABLE_HEIGHT), pos=(0.0, 0.0, TABLE_CENTER_Z), fixed=True),
        material=gs.materials.Rigid(friction=args.table_friction),
        surface=gs.surfaces.Default(color=(0.55, 0.38, 0.22, 1.0)),
    )
    cube_low = scene.add_entity(
        gs.morphs.Box(size=(CUBE_SIZE,) * 3, pos=(START_X, LOW_LANE_Y, RESTING_CENTER_Z)),
        material=gs.materials.Rigid(rho=500.0, friction=args.low_friction),
        surface=gs.surfaces.Default(color=(0.95, 0.50, 0.15, 1.0)),
    )
    cube_high = scene.add_entity(
        gs.morphs.Box(size=(CUBE_SIZE,) * 3, pos=(START_X, HIGH_LANE_Y, RESTING_CENTER_Z)),
        material=gs.materials.Rigid(rho=500.0, friction=args.high_friction),
        surface=gs.surfaces.Default(color=(0.15, 0.45, 0.85, 1.0)),
    )
    camera = scene.add_camera(
        res=(720, 400),
        pos=(1.25, -1.55, 1.35),
        lookat=(0.0, 0.0, 0.72),
        fov=46,
        GUI=False,
    )
    scene.build()

    # Establish the contact manifold before defining the horizontal-motion t=0.
    for _ in range(settle_steps):
        scene.step()

    start_low = to_numpy(cube_low.get_pos()).reshape(-1).copy()
    start_high = to_numpy(cube_high.get_pos()).reshape(-1).copy()
    initial_rgb = np.empty((0,), dtype=np.uint8)
    final_rgb = np.empty((0,), dtype=np.uint8)
    render_error = ""
    try:
        initial_rgb = to_numpy(camera.render(rgb=True)[0])
    except Exception as exc:
        render_error = f"{type(exc).__name__}: {exc}"

    initial_dofs_velocity = np.array([args.initial_vx, 0.0, 0.0, 0.0, 0.0, 0.0])
    cube_low.set_dofs_velocity(initial_dofs_velocity)
    cube_high.set_dofs_velocity(initial_dofs_velocity)

    time_values = np.arange(measure_steps + 1, dtype=float) * args.dt
    x_low = np.empty(measure_steps + 1, dtype=float)
    x_high = np.empty(measure_steps + 1, dtype=float)
    vx_low = np.empty(measure_steps + 1, dtype=float)
    vx_high = np.empty(measure_steps + 1, dtype=float)
    omega_y_low = np.empty(measure_steps + 1, dtype=float)
    omega_y_high = np.empty(measure_steps + 1, dtype=float)
    contacts_low = np.empty(measure_steps + 1, dtype=int)
    contacts_high = np.empty(measure_steps + 1, dtype=int)

    def record(index):
        x_low[index] = float(to_numpy(cube_low.get_pos()).reshape(-1)[0])
        x_high[index] = float(to_numpy(cube_high.get_pos()).reshape(-1)[0])
        vx_low[index] = float(to_numpy(cube_low.get_vel()).reshape(-1)[0])
        vx_high[index] = float(to_numpy(cube_high.get_vel()).reshape(-1)[0])
        omega_y_low[index] = float(to_numpy(cube_low.get_ang()).reshape(-1)[1])
        omega_y_high[index] = float(to_numpy(cube_high.get_ang()).reshape(-1)[1])
        contacts_low[index] = int(cube_low.get_contacts(with_entity=table)["position"].shape[0])
        contacts_high[index] = int(cube_high.get_contacts(with_entity=table)["position"].shape[0])

    record(0)
    for index in range(1, measure_steps + 1):
        scene.step()
        record(index)

    if not render_error:
        try:
            final_rgb = to_numpy(camera.render(rgb=True)[0])
        except Exception as exc:
            render_error = f"{type(exc).__name__}: {exc}"
            initial_rgb = np.empty((0,), dtype=np.uint8)

    stop_index_low = sustained_stop_index(vx_low, args.stop_speed, hold_samples)
    stop_index_high = sustained_stop_index(vx_high, args.stop_speed, hold_samples)
    stop_time_low = time_values[stop_index_low] if stop_index_low >= 0 else np.nan
    stop_time_high = time_values[stop_index_high] if stop_index_high >= 0 else np.nan
    stop_distance_low = x_low[stop_index_low] - x_low[0] if stop_index_low >= 0 else np.nan
    stop_distance_high = x_high[stop_index_high] - x_high[0] if stop_index_high >= 0 else np.nan
    # NOTEBOOK_CORE_END

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        dt=np.asarray(args.dt),
        substeps=np.asarray(args.substeps),
        substep_dt=np.asarray(args.dt / args.substeps),
        settle_duration=np.asarray(args.settle_duration),
        measure_duration=np.asarray(args.measure_duration),
        initial_vx=np.asarray(args.initial_vx),
        table_friction=np.asarray(args.table_friction),
        low_friction=np.asarray(args.low_friction),
        high_friction=np.asarray(args.high_friction),
        stop_speed=np.asarray(args.stop_speed),
        stop_hold=np.asarray(args.stop_hold),
        time=time_values,
        x_low=x_low,
        x_high=x_high,
        vx_low=vx_low,
        vx_high=vx_high,
        omega_y_low=omega_y_low,
        omega_y_high=omega_y_high,
        contacts_low=contacts_low,
        contacts_high=contacts_high,
        start_low=start_low,
        start_high=start_high,
        final_low=to_numpy(cube_low.get_pos()).reshape(-1),
        final_high=to_numpy(cube_high.get_pos()).reshape(-1),
        stop_time_low=np.asarray(stop_time_low),
        stop_time_high=np.asarray(stop_time_high),
        stop_distance_low=np.asarray(stop_distance_low),
        stop_distance_high=np.asarray(stop_distance_high),
        final_distance_low=np.asarray(x_low[-1] - x_low[0]),
        final_distance_high=np.asarray(x_high[-1] - x_high[0]),
        initial_rgb=initial_rgb,
        final_rgb=final_rgb,
        render_error=np.asarray(render_error),
    )
    print(
        f"saved {args.output} | low-μ stop={stop_time_low:.3f} s, {stop_distance_low:.3f} m | "
        f"high-μ stop={stop_time_high:.3f} s, {stop_distance_high:.3f} m"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
