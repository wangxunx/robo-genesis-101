---
lesson: L06
slug: parallel-simulation-and-batched-franka-control
locale: en
title: "Parallel Simulation and Batched Franka Control"
duration_minutes: 90
hardware: cpu-ok
status: planned
---

# L06 · Parallel Simulation and Batched Franka Control

> **Course status:** L06 remains `planned`. This page defines the complete
> English mechanism and experiment path, but the executable companion notebook
> and its clean-kernel evidence are not available yet. The code below is for
> focused reading; no numerical output is presented as a verified course run.

## Where this lesson fits

L05 followed one target pose through inverse kinematics (IK), joint-space
position control, repeated `scene.step()` calls, and a measured end-effector
pose. L06 keeps that chain and asks how its meaning changes when one Scene
contains a batch of environments:

> How can one declared topology produce four independent simulation states,
> how does the leading environment dimension flow through IK and control, and
> how can we update only selected environments without confusing row numbers
> with environment indices?

The central experiment has two stages:

```text
one Plane + Franka topology
  → build four environments
  → four target poses
  → batched IK and per-environment acceptance
  → batched PD targets and dynamic pose measurements
  → two new target poses for environments 1 and 3 only
  → selected and untouched evidence
```

This is a batching lesson, not a new robot task. There is no table, object,
grasp state machine, dataset, or learned policy. L07 will add the grasping
scene. L09 will later reuse the batch mental model when discussing
demonstration recording, but L06 does not implement a parallel recorder.

Before starting, you should be able to:

- explain the `init → declare → build → control → step → read/render`
  lifecycle;
- identify Franka's seven arm DOFs, two finger DOFs, and `(9,)` qpos;
- distinguish an IK candidate and six-dimensional residual from a measured
  dynamic pose;
- send an accepted q through position control instead of teleporting state;
- compare world-frame positions and `wxyz` quaternions; and
- treat a camera image as observation evidence, not a numerical acceptance
  test.

### A 90-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–8 min | Reconnect the L05 single-environment chain | State the unbatched q and pose shapes |
| 8–20 min | One topology, four independent states | Explain why layout spacing is not a physical target offset |
| 20–32 min | Leading environment dimension and shape ledger | Predict full-batch and selected-subset shapes |
| 32–47 min | Batched IK | Accept or reject every candidate row |
| 47–61 min | Batched dynamic execution | Measure pose error for all four environments |
| 61–77 min | Selective update of environments 1 and 3 | Explain row-to-environment mapping and retained targets |
| 77–84 min | Correctness, throughput, rendering, and recording | Name the evidence required by each claim |
| 84–88 min | Optional batched camera | Check RGB/depth leading dimensions or report a clear skip |
| 88–90 min | Checkpoint and exercise | Restate the full batch and subset contracts |

## Learning objectives

By the end of L06, you should be able to:

1. explain how `scene.build(n_envs=B)` turns one declared entity topology into
   B independent simulation states, while `env_spacing` changes only their
   visual arrangement;
2. extend L05 q, target pose, IK candidate, residual, and measured-pose shapes
   with a leading environment dimension;
3. solve B=4 IK targets in one batched call and accept candidates per
   environment using shape, finite-value, position-residual, and
   rotation-residual checks;
4. apply an accepted `(4, 9)` q array as PD position targets, advance every
   environment with repeated `scene.step()`, and measure each final pose;
5. use `envs_idx=[1, 3]` with exactly two target and command rows, and state
   which row maps to which environment;
6. explain why environments 0 and 2 retain active PD targets rather than
   becoming frozen, then check their motion and retained-target error change;
7. distinguish batching correctness, simulation throughput, batched
   rendering, and complete parallel data recording; and
8. validate optional batched RGB/depth shapes without using images as a
   substitute for IK and control evidence.

## One topology, B independent states

### Declare once, replicate at build time

As in earlier lessons, entities and optional cameras are declared before the
Scene is built. The difference appears at the build boundary:

```python
B = 4

scene = gs.Scene(...)
scene.add_entity(gs.morphs.Plane())
franka = scene.add_entity(
    gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml")
)

scene.build(
    n_envs=B,
    env_spacing=(1.1, 1.1),
    n_envs_per_row=2,
)
```

The declarations describe one Plane-and-Franka topology: the entity types,
links, DOF names, and controller configuration shared by every replica.
`build(n_envs=4)` creates four copies of the simulation state. Each copy has
its own q, qdot, controller targets, contacts, and evolving dynamics.

The distinction is important:

```text
shared topology and parameters
          │
          └── build(n_envs=4)
                ├── environment 0 state
                ├── environment 1 state
                ├── environment 2 state
                └── environment 3 state
```

The environments are independent state replicas, not four differently
declared robots. A command can name a subset of those states, while one
`scene.step()` still advances all four.

### `n_envs=0` and `n_envs>0` have different shape contracts

In Genesis 1.3.3, `n_envs=0` means an unbatched Scene. It does not mean that
the Scene contains no physical environment. State and command arrays then have
no leading environment dimension: Franka qpos is `(9,)` and a hand position is
`(3,)`.

When `n_envs>0`, the first dimension is the environment dimension. With
`n_envs=4`, those shapes become `(4, 9)` and `(4, 3)`. Even `n_envs=1` is
batched and therefore keeps a length-one leading dimension such as `(1, 9)`.
Do not write code that treats `n_envs=1` as equivalent to `n_envs=0`.

### Layout offsets are not simulation coordinates

`env_spacing`, `n_envs_per_row`, and `center_envs_at_origin` arrange replicas
for visualization. They help a viewer or overview camera show multiple robots
without drawing them on top of one another. Genesis explicitly treats these
offsets as visualization-only; they do not change simulation-related poses.

Suppose environment 3 is drawn to the right of environment 1 in a 2×2 visual
grid. A world-frame IK target of `[0.45, 0.10, 0.35]` still has that same
physical meaning inside either environment. Do not add the displayed grid
offset to the target position.

::: warning Do not control the visualization layout
Adding `env_spacing` to IK targets double-counts an offset that Genesis applies
only while drawing the replicas. The resulting target may become unreachable,
and the numerical state will no longer mean what the picture suggests.
:::

## The leading environment dimension

L05 used one q row and one target pose. L06 changes the leading dimension, not
the meaning of each row.

Let:

- `B=4` be the number of built environments;
- `D=9` be the number of Franka DOFs; and
- `K=2` be the number of selectively addressed environments.

### Shape ledger

| Quantity | Unbatched L05 | Full batch, B=4 | Selected `envs_idx=[1, 3]` | Meaning of one row |
|---|---:|---:|---:|---|
| qpos / joint command | `(9,)` | `(4, 9)` | `(2, 9)` | Nine Franka joint values |
| Target position | `(3,)` | `(4, 3)` | `(2, 3)` | One world-frame xyz target |
| Target quaternion | `(4,)` | `(4, 4)` | `(2, 4)` | One unit `wxyz` orientation |
| IK residual | `(6,)` | `(4, 6)` | `(2, 6)` | xyz plus rotation-vector residual |
| Measured hand position | `(3,)` | `(4, 3)` | Read all, then select rows | One world-frame xyz measurement |
| Measured hand quaternion | `(4,)` | `(4, 4)` | Read all, then select rows | One measured `wxyz` orientation |

For a full-batch call, row `i` belongs to environment `i`. For a selective
call, row numbers and environment indices are different namespaces:

```text
envs_idx = [1, 3]

input/output row 0  ↔  environment 1
input/output row 1  ↔  environment 3
```

The leading dimension of every selective input must therefore equal
`len(envs_idx)`, not `B`. A `(4, 9)` command paired with two indices is not a
selective command. Neither is a `(2, 9)` command with no `envs_idx`, because
Genesis would then expect a row for every environment.

Avoid relying on broadcasting to repair a missing batch dimension. Explicit
rows make target ownership visible, let each environment receive a distinct
pose, and expose mapping errors before control begins.

## Baseline: batched IK for four environments

The baseline assigns one reachable world-frame hand pose to each environment.
The positions differ, while all four rows use the same normalized `wxyz`
orientation:

```python
target_positions = np.array([
    [0.42, -0.12, 0.35],  # environment 0
    [0.48, -0.04, 0.40],  # environment 1
    [0.48,  0.06, 0.32],  # environment 2
    [0.40,  0.14, 0.38],  # environment 3
])
target_quaternions = np.tile(
    np.array([0.0, 1.0, 0.0, 0.0]),  # w, x, y, z
    (B, 1),
)
```

Their shapes are `(4, 3)` and `(4, 4)`. They are simulation world-frame
targets; none contains an `env_spacing` offset.

The batched solve preserves the L05 IK contract:

`hand` and `arm_dofs` are resolved by link and joint names exactly as in
L04/L05; do not replace them with assumed scene-global indices.

```python
q_start = franka.get_qpos()
q_goal_raw, ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=target_positions,
    quat=target_quaternions,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=5e-4,
    rot_tol=5e-3,
    return_error=True,
)

q_goal = to_numpy(q_goal_raw)
ik_error = to_numpy(ik_error_raw)
```

The expected output shapes are:

```text
q_goal.shape   == (4, 9)
ik_error.shape == (4, 6)
```

Although IK is solved through the seven arm DOFs, the returned entity q row
contains all nine Franka DOFs. The two finger values remain part of the row.

### Accept every row, not an average

For environment `i`, the residual has two parts:

```text
ik_error[i, :3]  position residual vector, metres
ik_error[i, 3:]  rotation-vector residual, radians
```

Reduce them row-wise:

```python
position_residuals = np.linalg.norm(ik_error[:, :3], axis=1)
rotation_residuals = np.linalg.norm(ik_error[:, 3:], axis=1)

candidate_valid = (
    np.isfinite(q_goal).all(axis=1)
    & np.isfinite(ik_error).all(axis=1)
    & (position_residuals <= 5e-4)
    & (rotation_residuals <= 5e-3)
)
```

First assert the exact array shapes and normalized quaternion rows. Then
require all four Boolean values in `candidate_valid` to be true before sending
the full-batch command.

A mean residual can hide a failed row. For example, three very small values
can pull the mean below tolerance even when the fourth environment did not
converge. A maximum is a useful summary, but the row-wise values and labels
must remain visible:

```text
env 0: position residual ..., rotation residual ..., accepted ...
env 1: position residual ..., rotation residual ..., accepted ...
env 2: position residual ..., rotation residual ..., accepted ...
env 3: position residual ..., rotation residual ..., accepted ...
```

As in L05, a finite q is only a candidate. IK does not move the robot and does
not produce a collision-free path. In this lesson, if any baseline row fails,
stop the stage and diagnose it rather than sending a mixture of accepted and
rejected candidates.

## Batched dynamic execution

Once all four candidates pass, use them as position-controller targets:

```python
franka.control_dofs_position(q_goal)

for _ in range(180):
    scene.step()
```

The first call updates all four PD targets because `envs_idx` is omitted and
the command has four rows. Each subsequent `scene.step()` advances all four
environment states. Increasing B does not increase the simulated `dt`; it
increases how many state replicas participate in that step.

After the fixed observation window, read the hand poses in the same world
frame used by IK:

```python
measured_positions = to_numpy(hand.get_pos(relative=False))
measured_quaternions = to_numpy(hand.get_quat(relative=False))

position_errors = np.linalg.norm(
    measured_positions - target_positions,
    axis=1,
)

def quaternion_angle_error_rows(measured_wxyz, target_wxyz):
    measured_wxyz = np.asarray(measured_wxyz, dtype=float)
    target_wxyz = np.asarray(target_wxyz, dtype=float)
    measured = measured_wxyz / np.linalg.norm(
        measured_wxyz,
        axis=1,
        keepdims=True,
    )
    target = target_wxyz / np.linalg.norm(
        target_wxyz,
        axis=1,
        keepdims=True,
    )
    cosine_half_angle = np.clip(
        np.abs(np.sum(measured * target, axis=1)),
        0.0,
        1.0,
    )
    return 2.0 * np.arccos(cosine_half_angle)

orientation_errors = quaternion_angle_error_rows(
    measured_quaternions,
    target_quaternions,
)
```

`quaternion_angle_error_rows()` applies the L05 shortest-angle calculation to
each normalized quaternion pair. The absolute quaternion dot product makes
the calculation insensitive to the equivalent `q` and `-q` representations.
Its result has shape `(4,)`, just like `position_errors`.

For this Plane-and-Franka experiment and finite control window, the operational
dynamic checks are:

| Check | Per-environment requirement |
|---|---:|
| Final position error | `<0.02 m` |
| Final orientation error | `<0.05 rad` |
| Position error relative to the initial pose | Decreases |

These are experiment-specific acceptance thresholds, not claims about a real
Franka, arbitrary targets, or long-term controller accuracy. The future
companion notebook must verify them on every row before they become runtime
evidence.

### Solver evidence and dynamics evidence remain separate

| Evidence | Question answered | What it does not prove |
|---|---|---|
| Per-environment IK residual | Did each candidate satisfy the numerical pose tolerance? | Did any robot move? |
| Batched command shape and mapping | Did each candidate row address the intended environment? | Did the controller track it? |
| Per-environment measured pose error | Where did each dynamic hand end after stepping? | Was the path collision-free? |

Do not replace the controller with `set_dofs_position()`. A state reset would
make the final pose appear correct while removing the PD controller and
dynamics that this stage is meant to test.

## Selective update: environments 1 and 3

The second stage changes only two targets:

```python
selected_envs = [1, 3]
untouched_envs = [0, 2]

selected_target_positions = np.array([
    [0.44, -0.16, 0.32],  # row 0 → environment 1
    [0.50,  0.12, 0.40],  # row 1 → environment 3
])
selected_target_quaternions = np.tile(
    np.array([0.0, 1.0, 0.0, 0.0]),
    (len(selected_envs), 1),
)
```

Here `selected_target_positions[0]` does not belong to environment 0. It
belongs to `selected_envs[0]`, which is environment 1. The second row belongs
to environment 3.

Use the same index list for IK and control:

```python
q_selected_raw, selected_ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=selected_target_positions,
    quat=selected_target_quaternions,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=5e-4,
    rot_tol=5e-3,
    return_error=True,
    envs_idx=selected_envs,
)

q_selected = to_numpy(q_selected_raw)
selected_ik_error = to_numpy(selected_ik_error_raw)
```

The selective shapes are exactly:

```text
selected_target_positions.shape   == (2, 3)
selected_target_quaternions.shape == (2, 4)
q_selected.shape                  == (2, 9)
selected_ik_error.shape           == (2, 6)
```

Apply the same per-row finite, position-residual `<=5e-4 m`, and
rotation-residual `<=5e-3 rad` checks. Only after both rows pass should the
controller receive them:

```python
positions_before_selective = measured_positions.copy()
baseline_position_errors = position_errors.copy()

franka.control_dofs_position(q_selected, envs_idx=selected_envs)
for _ in range(180):
    scene.step()
```

This replaces the PD targets for environments 1 and 3. It does not overwrite
the targets held by environments 0 and 2.

### Untouched does not mean frozen

Environments 0 and 2 receive no new command, but `scene.step()` still advances
them. Their existing PD controllers continue tracking the baseline q targets.
They may finish a small amount of residual convergence or respond to ordinary
numerical dynamics. Calling them “frozen” would predict zero state change for
the wrong reason.

The evidence must therefore answer two different questions:

1. Did environments 1 and 3 reach their new targets?
2. Did environments 0 and 2 retain their old targets without material
   degradation?

After the selective window, read all four poses. Compare selected rows with the
two new targets and untouched rows with their original baseline targets:

```python
positions_after = to_numpy(hand.get_pos(relative=False))
quaternions_after = to_numpy(hand.get_quat(relative=False))

selected_position_errors = np.linalg.norm(
    positions_after[selected_envs] - selected_target_positions,
    axis=1,
)
retained_position_errors = np.linalg.norm(
    positions_after[untouched_envs] - target_positions[untouched_envs],
    axis=1,
)
selected_orientation_errors = quaternion_angle_error_rows(
    quaternions_after[selected_envs],
    selected_target_quaternions,
)
retained_orientation_errors = quaternion_angle_error_rows(
    quaternions_after[untouched_envs],
    target_quaternions[untouched_envs],
)
untouched_motion = np.linalg.norm(
    positions_after[untouched_envs]
    - positions_before_selective[untouched_envs],
    axis=1,
)
retained_error_change = (
    retained_position_errors
    - baseline_position_errors[untouched_envs]
)
```

Compute selected and retained orientation errors with the corresponding
quaternion target rows as well. Then apply these per-environment checks:

| Group | Evidence | Requirement |
|---|---|---:|
| Selected env 1 and 3 | Position error to new target | `<0.02 m` |
| Selected env 1 and 3 | Orientation error to new target | `<0.05 rad` |
| Untouched env 0 and 2 | Position error to retained target | `<0.02 m` |
| Untouched env 0 and 2 | Orientation error to retained target | `<0.05 rad` |
| Untouched env 0 and 2 | Motion during selective window | `<0.005 m` |
| Untouched env 0 and 2 | Retained position-error increase | `<=0.002 m` |

The last two checks work together. Small motion alone does not say whether an
environment moved toward or away from its retained target. A small final error
alone could hide a noticeable regression from a better baseline. Reporting
motion, old error, new error, and error change makes the interpretation
auditable.

These finite-window checks support the narrow claim that the selected command
did not materially disturb the retained targets in this experiment. They do
not prove asynchronous reset, arbitrary-B isolation, or long-term stability.

## Four meanings that must stay separate

“Parallel simulation” is easily overloaded. L06 uses four distinct claims:

| Claim | Evidence needed here | Not established by that evidence |
|---|---|---|
| Batching correctness | Shapes, row mapping, finite values, residuals, and dynamic errors per environment | Faster wall-clock execution |
| Simulation throughput | A controlled timing protocol with warm-up, fixed backend and workload, synchronization, and rendering excluded | Correct target ownership or control |
| Batched rendering | Real RGB/depth arrays with a leading environment dimension | Correct IK, dynamic tracking, or recording |
| Complete parallel data recording | Action/observation alignment, environment and episode identity, reset semantics, encoding, and writer backpressure | Better policy quality |

One `scene.step()` advances B states, so N calls produce B×N environment
transitions. That API fact is not a measured speedup. Wall-clock throughput
depends on backend, B, scene complexity, kernel compilation, synchronization,
rendering, and data transfer. This lesson does not claim that B=4 is “4×
faster,” and it sets no FPS or transitions-per-second acceptance threshold.

If you later benchmark throughput, warm up first, synchronize at timing
boundaries, keep physics and rendering workloads fixed, and report both steps
per second and environment transitions per second. Do not mix a correctness
run with a performance conclusion.

## Optional batched camera observation

The numerical IK/control path is the minimum CPU path. When rendering is
explicitly enabled, Genesis 1.3.3's Rasterizer can return one image per rendered
environment by configuring `VisOptions` before the Scene is built:

```python
vis_options = gs.options.VisOptions(
    rendered_envs_idx=[0, 1, 2, 3],
    env_separate_rigid=True,
)

scene = gs.Scene(
    ...,
    vis_options=vis_options,
)
camera = scene.add_camera(
    res=(640, 360),
    pos=(1.2, -1.2, 1.0),
    lookat=(0.35, 0.0, 0.35),
    fov=45,
    GUI=False,
)

# Add entities, then call scene.build(n_envs=4, ...).
```

With `rendered_envs_idx=[0, 1, 2, 3]` and
`env_separate_rigid=True`, a render should have these shapes:

```python
rgb, depth, _, _ = camera.render(rgb=True, depth=True)

rgb.shape    == (4, 360, 640, 3)
depth.shape  == (4, 360, 640)
```

As in L05, camera configuration uses `res=(W, H)`, while the arrays use height
before width. The new first dimension follows `rendered_envs_idx`; each row is
one rendered environment. Check that RGB is non-empty `uint8`, depth is a
finite floating array, and all four images contain the Franka and ground
reference. A 2×2 mosaic is a useful display, but the original four-dimensional
RGB array is the batch evidence.

Without `env_separate_rigid=True`, the Rasterizer can instead draw multiple
visually offset replicas into one overview image. That single `(H, W, 3)` image
is not a batched image stack.

When rendering is disabled, report an explicit camera `SKIP`. Do not create
placeholder arrays or substitute a Matplotlib robot sketch. When it is enabled,
real camera arrays show that batched observation is available; they still do
not replace residual, command-mapping, or dynamic-pose checks.

## Companion lab

The companion lab follows one Plane-and-Franka topology through a full-batch
baseline and one selective update. It will expose the target arrays,
`envs_idx`, IK calls, validity vectors, controller calls, and per-environment
error calculations directly rather than hiding them in a black-box runner.

### Predict before running

Write down the answers before executing the experiment:

1. What qpos shape follows `build(n_envs=4)`?
2. Does the displayed location of environment 3 change its world-frame IK
   target?
3. If one of four residuals fails, can a passing mean make the batch valid?
4. With `envs_idx=[1, 3]`, which environment owns command row 0?
5. After the selective command, does `scene.step()` advance environments 0 and
   2?
6. Does RGB shape `(4, H, W, 3)` prove that the four IK candidates converged?

### Minimal numerical path

With rendering disabled, the lab should still complete the core lesson:

1. initialize one supported backend and declare Plane plus Franka;
2. build with `n_envs=4` and confirm qpos `(4, 9)`;
3. create four explicit world-frame target rows and normalized `wxyz` rows;
4. solve batched IK and accept every residual row;
5. apply the accepted `(4, 9)` PD target and step the whole Scene;
6. measure four position and orientation errors;
7. solve and apply two new rows through `envs_idx=[1, 3]`;
8. measure selected-target errors, retained-target errors, untouched motion,
   and retained-error change; and
9. print either the requested camera evidence or an explicit render `SKIP`.

No exception is not a pass. A successful run needs the exact shape contract,
finite values, and every per-environment numerical check.

## Common failures and a diagnostic order

### qpos is `(9,)` instead of `(4, 9)`

Confirm that the actual build call used `n_envs=4`. Creating a variable named
`B` or declaring one robot does not add a batch dimension. Remember that a
Scene can be built only after all entities and cameras have been declared.

### Targets are shifted or unreachable in later visual rows

Remove any manually added `env_spacing` or grid offset. Print the numerical
target rows separately from visual layout settings. IK receives simulation
world-frame poses, not screen placement.

### IK raises a leading-dimension error

Print `target_positions.shape`, `target_quaternions.shape`, and
`len(envs_idx)` at the call site. Full-batch inputs need four rows. A selective
call for `[1, 3]` needs two rows.

### The mean residual passes but one robot does not

Print position and rotation residual norms with environment labels. Apply the
tolerances to a Boolean vector, not only a scalar mean. Do not send the
full-batch command if any row fails.

### The wrong environments move toward new targets

Print `(row, env_idx, target)` before both selective IK and control. Reuse the
same ordered, unique `envs_idx` list in both calls. Do not index a two-row
result as if its row numbers were global environment indices.

### An untouched environment moves slightly

Do not immediately call this cross-environment interference. Environments 0
and 2 still have active baseline PD targets. Compare before/after motion,
retained-target error, and error change together. Then inspect whether the
wrong index list or command array was used.

### IK passes but dynamic pose error fails

Check that the accepted q reached `control_dofs_position()`, the full step
window ran, DOF order and gains match the L04/L05 configuration, and the final
pose was read afterward with `relative=False`. Inspect each trajectory for
non-finite values or an error that stopped decreasing. Do not use a state reset
to make the assertion pass.

### RGB has no environment dimension

Confirm that `VisOptions(env_separate_rigid=True)` and the intended
`rendered_envs_idx` were supplied before build. A single overview image is a
different rendering mode, not failed numerical batching.

### B=4 is slower than expected

Separate first-build compilation, rendering, synchronization, and array copies
from steady-state stepping. Correct batch semantics do not require a fixed
speedup.

Use this diagnostic order:

```text
version, backend, and render mode
  → declare/build boundary and B
  → numerical frames versus visual spacing
  → full-batch or subset shapes
  → row-to-environment mapping
  → per-row IK residuals
  → PD targets and step window
  → measured state and per-environment errors
  → optional camera shapes or throughput measurement
```

## Checkpoints and exercise

### Concept checkpoints

Answer these without looking back:

1. What does `n_envs=0` mean, and how is `n_envs=1` different?
2. Which properties are shared topology and which are per-environment state?
3. Why must `env_spacing` not be added to a world-frame IK target?
4. What are the full-batch shapes of q, position, quaternion, and IK residual
   for B=4?
5. What are those shapes for `envs_idx=[1, 3]`, and how do the two rows map?
6. Why can neither a mean residual nor a camera mosaic replace row-wise
   acceptance?
7. Why are environments 0 and 2 still dynamic after only 1 and 3 receive new
   commands?
8. What evidence distinguishes batch correctness from throughput, batched
   rendering, and complete data recording?

### Hands-on exercise: select environments 0 and 2

After the baseline succeeds, change only the selective stage:

```python
selected_envs = [0, 2]
untouched_envs = [1, 3]
selected_target_positions = np.array([
    [0.46, -0.08, 0.38],  # row 0 → environment 0
    [0.44,  0.10, 0.36],  # row 1 → environment 2
])
```

Keep B, orientation, controller settings, step count, and rendering mode
unchanged. Before running, predict the position, quaternion, q, and residual
shapes and write the row mapping.

Then report, per environment:

1. the two selected IK residual pairs;
2. the selected final position and orientation errors;
3. the untouched final errors to their original baseline targets;
4. untouched motion and retained position-error change; and
5. whether any camera batch shape changed.

Do not increase B, add an object, or time the run. Those changes would make it
harder to tell whether a result came from the new index mapping or another
variable.

## Summary and connections

- `build(n_envs=B)` replicates one declared topology into B independent states.
  `n_envs=0` is unbatched; every positive value adds a leading environment
  dimension.
- `env_spacing` and `n_envs_per_row` control visual layout only. World-frame IK
  targets do not include those offsets.
- With B=4, q/command, position, quaternion, and IK residual shapes are
  `(4, 9)`, `(4, 3)`, `(4, 4)`, and `(4, 6)`.
- With `envs_idx=[1, 3]`, those shapes begin with 2. Row 0 maps to environment
  1, and row 1 maps to environment 3.
- Every IK candidate needs its own shape, finite-value, position-residual, and
  rotation-residual checks before it becomes a PD target.
- One `scene.step()` advances every environment. Measure position and
  orientation errors for each row after the dynamic control window.
- An unselected environment retains its previous PD target; it is not frozen.
  Use both motion and retained-error change to check selective isolation.
- Batching correctness, throughput, batched rendering, and complete parallel
  recording are separate claims with separate evidence. B=4 does not imply a
  fixed 4× wall-clock speedup.

L07 will keep the control and indexing discipline while adding a tabletop
grasping scene. L09 will later need the same leading-dimension and environment
identity discipline for action/observation recording. This lesson does not
establish collision-free paths, arbitrary-B stability, asynchronous reset,
long-term stability, recorder correctness, policy benefit, or grasp success.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `Scene` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/scene.py)
  — version-pinned `build()`, batch-dimension, and visualization-offset
  behavior.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned batched IK, state access, and selective position-control
  behavior.
- [Genesis 1.3.3 `Camera` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — version-pinned rendering and batched image return behavior.
- [Genesis 1.3.3 `VisOptions` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/options/vis.py)
  — version-pinned environment selection and separate-rigid rendering options.
- [Genesis 1.3.3 bundled Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — the robot model, joints, limits, and actuator configuration used here.
