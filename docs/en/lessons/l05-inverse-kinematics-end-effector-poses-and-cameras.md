---
lesson: L05
slug: inverse-kinematics-end-effector-poses-and-cameras
locale: en
title: "Inverse Kinematics, End-Effector Poses, and Cameras"
duration_minutes: 120
hardware: cpu-ok
status: planned
---

# L05 · Inverse Kinematics, End-Effector Poses, and Cameras

> **Course status:** the English lecture text is present. The paired Chinese
> lecture and the executable notebooks are still being developed, so L05
> remains `planned`; this page does not claim runtime verification or
> publication of the complete bilingual lesson.

## Where this lesson fits

L04 established how a named joint target becomes measured motion through a
controller, actuator limits, dynamics, and repeated calls to `scene.step()`.
L05 adds the layer that chooses the seven arm-joint targets: a desired pose for
the Franka hand in task space. It also promotes cameras from optional scene
illustrations to sensors with explicit frames, projection parameters, and array
contracts.

The central question is:

**How can a world-frame hand pose be converted into an acceptable joint-space
candidate, executed through dynamics, and measured both as a pose and through
fixed and hand-attached cameras?**

The complete reasoning chain is:

```text
world-frame target pose T_WH*
          ↓  IK + masks + limits + residual checks
candidate q_goal
          ↓  L04 controller + dynamics + scene.step()
measured hand pose T_WH(t)
          ↓  position/orientation error + Jacobian evidence
bounded claim about execution

fixed camera: T_WC is constant
wrist camera: T_WC(t) = T_WH(t) T_HC
scene state + T_CW + K + near/far → RGB and depth arrays
```

An IK call returning without an exception is not enough evidence. A finite
joint vector can be a best-effort answer for an unreachable target. A small
solver residual does not prove that the dynamic robot reached the pose. A
plausible RGB frame does not establish either claim. L05 keeps these evidence
layers separate and reconnects them explicitly.

Before starting, you should be able to:

- explain `gs.init → Scene → add_entity/add_camera → build → step/read/render`;
- resolve Franka's seven arm DOFs and two finger DOFs by joint name;
- distinguish `set_dofs_position(...)` from
  `control_dofs_position(...)`;
- check shapes, units, position limits, and finite values; and
- interpret a finite control window using measured state rather than only a
  final image.

No table, YCB object, grasp state machine, dataset, or learned policy is needed.
The numerical IK and control path is CPU-capable. Rendering is an explicit,
separate capability: if it is requested, it must work rather than silently
falling back to a drawing.

### A 120-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–10 min | Reconnect target generation to the L04 controller | Predict what finite q, low residual, low tracking error, and a camera frame can each prove |
| 10–27 min | World, base, hand, and camera frames; pose and quaternion conventions | Decide whether two quantities are expressed in a common frame |
| 27–43 min | Forward kinematics, the 6×7 arm Jacobian, redundancy, and singularity | Explain the local velocity map and why an IK solution need not be unique |
| 43–56 min | Damped IK, masks, initial guesses, limits, and tolerances | Write an acceptance rule that does not equate finite output with success |
| 56–78 min | Reachable target: IK, FK, dynamic control, and measured pose | Build a target→candidate→execution evidence chain |
| 78–94 min | Fixed and attached cameras, K, extrinsics, RGB, and depth | Verify sensor frames and array semantics |
| 94–107 min | Unreachable target and explicit diagnostic execution | Distinguish rejection, best effort, and task success |
| 107–116 min | Four-environment IK and selective updates | Track the batch dimension and inspect every environment |
| 116–120 min | Checkpoints, evidence boundary, and handoff | State what L06, L07, and L08 can safely reuse |

## Learning objectives

By the end of L05, you should be able to:

1. distinguish world, robot-base, hand-link, and camera frames, and compose a
   short chain of homogeneous transforms using one declared convention;
2. represent a pose as position plus orientation, validate Genesis's w-x-y-z
   quaternion convention, and compute an angular error that respects the
   `q`/`-q` double cover;
3. explain forward kinematics, the local spatial Jacobian, redundancy,
   manipulator singularity, and damped least-squares IK without conflating them
   with path planning or Euler-angle gimbal lock;
4. call `inverse_kinematics(..., return_error=True)` for the arm DOFs and
   validate the returned shape, finiteness, joint limits, finger preservation,
   and enabled position/rotation residuals;
5. distinguish solver residual, FK prediction error, and dynamic execution
   error, then use the L04 controller to test whether an accepted candidate is
   reached in a finite time window;
6. explain why an unreachable target can still produce a finite best-effort
   joint vector and why a diagnostic override is not a production strategy;
7. interpret camera resolution, vertical FOV, intrinsic matrix, world-to-camera
   extrinsics, clipping planes, RGB shape, and metric depth validity;
8. manage the lifecycle of a fixed camera and a hand-attached camera, including
   `add_camera(...)`, `attach(...)`, and `move_to_attach()`;
9. reason about `(B, ...)` arrays in a four-environment IK/control experiment
   and verify a selective `envs_idx=[1, 3]` update per environment; and
10. diagnose frame, quaternion, reachability, control, and camera failures in a
    dependency-aware order.

## Frames before coordinates

### A name tells us where a quantity lives

Coordinates are meaningful only together with a reference frame. L05 uses four
frames:

| Frame | Symbol | Role in this lesson |
|---|---|---|
| World | W | Common frame for targets, measured hand poses, and the fixed camera |
| Robot base | B | Root frame of the imported Franka model |
| Hand link | H | End-effector link frame used by FK, the Jacobian, and IK |
| Camera | C | Optical frame used with camera intrinsics and extrinsics |

The base happens to coincide with the world in this lesson's fixed-base scene.
That is a scene configuration, not a general identity. A robot mounted on a
table, a mobile base, or a replicated environment can have a non-identity
world-to-base transform.

Genesis 1.3.3 documents the `pos` and `quat` targets passed to
`inverse_kinematics(...)` as world-frame quantities. The world-frame hand pose
can be read with:

```python
hand_position = hand.get_pos(relative=False)
hand_quaternion = hand.get_quat(relative=False)
```

Subtracting a camera-frame point directly from `hand_position` would be
invalid. One of them must first be transformed so both are expressed in the
same frame.

### One transform convention

This lesson writes `T_AB` for the homogeneous transform that converts
coordinates expressed in frame B into coordinates expressed in frame A. For a
point `p_B` written in homogeneous coordinates:

```text
p_A = T_AB p_B
```

Transform chains follow their subscripts:

```text
T_AC = T_AB T_BC
T_CA = inverse(T_AC)
```

For a camera rigidly mounted to the hand, `T_HC` is the fixed mounting offset.
The camera's world pose changes with the hand:

```text
T_WC(t) = T_WH(t) T_HC
```

The fixed camera instead has a configured `T_WC` that should remain constant as
the robot moves. Genesis exposes camera extrinsics as a world-to-camera matrix,
which this convention calls `T_CW`, not `T_WC`. Confusing a pose with its inverse
is one of the easiest ways to produce plausible but mirrored or displaced
geometry.

A 4×4 transform has the form:

```text
T_AB = [ R_AB  p_AB ]
       [  0       1 ]
```

where `R_AB` is a 3×3 rotation and `p_AB` is the origin of B expressed in A.
L05 needs composition and inversion, but not a full derivation of rigid-body
transform theory.

## A pose is position plus orientation

A 3D position alone does not specify how the hand is oriented. The target pose
contains both:

```text
position:     [x, y, z] in metres
orientation:  unit quaternion [w, x, y, z]
```

The quaternion order is an API contract. Genesis uses **w-x-y-z**. A value from
a library that returns x-y-z-w cannot be copied without reordering.

### Normalize before comparing

A rotation quaternion must have unit norm. A strict input check can normalize
small floating-point drift while rejecting an invalid or nearly zero vector:

```python
import numpy as np


def normalize_wxyz(quaternion):
    quaternion = np.asarray(quaternion, dtype=float)
    if quaternion.shape != (4,) or not np.isfinite(quaternion).all():
        raise ValueError("quaternion must be a finite wxyz vector of shape (4,)")
    norm = np.linalg.norm(quaternion)
    if norm < 1e-12:
        raise ValueError("a zero quaternion does not define an orientation")
    return quaternion / norm
```

Normalization repairs representation scale; it does not repair a wrong
component order or a target expressed in the wrong frame.

### `q` and `-q` are the same rotation

Unit quaternions double-cover the rotation group: `q` and `-q` represent the
same physical orientation. Component-wise subtraction therefore gives a false
large error for some identical orientations.

For normalized measured and target quaternions, use the shortest angular
distance:

```python
def quaternion_angle_error(measured_wxyz, target_wxyz):
    measured = normalize_wxyz(measured_wxyz)
    target = normalize_wxyz(target_wxyz)
    cosine_half_angle = np.clip(abs(np.dot(measured, target)), 0.0, 1.0)
    return 2.0 * np.arccos(cosine_half_angle)
```

The absolute dot product handles the double cover, clipping protects `arccos`
from floating-point excursions, and the result lies from 0 to pi radians. This
is the dynamic orientation metric used in the lab.

Quaternions avoid the coordinate singularity known as Euler-angle gimbal lock.
They do not remove the unit-norm constraint, the double cover, or kinematic
singularities of a robot arm. Those are separate issues.

## Forward kinematics and the Jacobian

### Forward kinematics asks what pose a configuration produces

Forward kinematics (FK) is the deterministic mapping:

```text
q → T_WH(q)
```

For the pinned Genesis API, `forward_kinematics(...)` accepts joint
configuration data and returns world-frame link positions and quaternions. It
is a prediction for the supplied configuration. It does not send a controller
command, advance dynamics, or move the current scene.

This distinction supports two different checks:

```text
FK prediction:      q_goal → predicted hand pose
dynamic execution:  command q_goal → scene.step() → measured hand pose
```

A candidate can have a good FK pose but still be tracked poorly because the
control window is short, actuator effort is limited, the robot is moving, or
the dynamic model introduces error.

### The Jacobian is a local velocity map

At a configuration `q`, the spatial Jacobian relates joint velocity to the
linear and angular velocity of the hand:

```text
[v]
[ω] ≈ J(q) qdot
```

Genesis returns the translational rows first and the rotational rows second.
For the complete fixed-base Franka entity, `get_jacobian(hand)` has shape
`(6, 9)`. Selecting the seven named arm columns gives the `(6, 7)` arm
Jacobian used by IK reasoning in this lesson.

The approximation is local. If `q` changes substantially, so does `J(q)`. A
Jacobian measured at the initial pose is not a global map of the workspace.

### Seven arm variables for a six-dimensional pose

The hand pose has three position and three orientation dimensions. The Franka
arm has seven joint variables. Away from constraints and singularities, that
extra variable makes the arm kinematically redundant for a six-dimensional
pose task.

Redundancy has useful consequences and important limits:

- several configurations may produce the same hand pose;
- the returned solution can depend on the initial guess;
- joint limits can remove otherwise valid branches;
- a mask can reduce the number of constrained task dimensions; and
- a secondary objective could prefer one posture, although L05 does not design
  such an objective.

An IK answer is therefore **a** candidate, not **the** unique configuration.

### Manipulator singularity is not gimbal lock

The singular values of the arm Jacobian describe local motion capability. If a
singular value is small, motion in a corresponding task-space direction can
require a large joint-space change. At rank loss, an instantaneous direction
cannot be produced by the available joint velocities at that configuration.

This is a manipulator singularity: a property of the robot and pose. Gimbal
lock is a coordinate singularity of a particular Euler-angle parameterization.
Using a quaternion avoids the latter but not the former.

The notebook reports finite Jacobian singular values for the measured
configuration. It does not impose a universal condition-number threshold or
claim that one sample proves the entire workspace nonsingular.

## Inverse kinematics is a constrained numerical search

IK reverses the FK question:

```text
desired T_WH* → one q candidate whose FK pose approximates T_WH*
```

For an arm-only solve in Genesis 1.3.3, the teaching call has this structure:

```python
q_candidate, residual = franka.inverse_kinematics(
    link=hand,
    pos=target_position,
    quat=target_quaternion,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    damping=0.01,
    pos_tol=position_tolerance,
    rot_tol=rotation_tolerance,
    pos_mask=[True, True, True],
    rot_mask=[True, True, True],
    return_error=True,
)
```

For the current unbatched Franka, the returned whole-entity candidate has shape
`(9,)` and the residual has shape `(6,)`. The residual ordering is:

```text
[position error x, position error y, position error z,
 rotation-vector error x, rotation-vector error y, rotation-vector error z]
```

The default tolerances in the pinned signature are `5e-4 m` for position and
`5e-3 rad` for rotation. A lab may pass its values explicitly so that the
acceptance contract is visible rather than inherited invisibly.

### Damped least squares

Around the current configuration, IK repeatedly linearizes pose error using the
Jacobian. A damped least-squares update has the form:

```text
delta_q = J^T (J J^T + lambda^2 I)^-1 error
```

The damping term `lambda` regularizes the inversion and reduces extreme updates
near small singular values. It does not create a missing degree of freedom or
make an unreachable target reachable. Too little damping can make updates
sensitive near a singularity; too much can make progress conservative.

### Initial guess, masks, and limits change the problem

Four arguments deserve explicit interpretation:

- `init_qpos` selects where the numerical search begins. With redundancy,
  different starting postures can lead to different candidates.
- `dofs_idx_local=arm_dofs` prevents the solver from treating the fingers as
  pose variables. The returned finger coordinates should remain equal to the
  intended gripper state.
- `pos_mask` and `rot_mask` specify which task-space components matter. A
  disabled component must not later be presented as a solved constraint.
- `respect_joint_limit=True` bounds the search using model limits. A candidate
  within limits may still have excessive residual; limit validity is necessary
  but not sufficient.

The current solver starts from scene qpos when `init_qpos` is omitted and
restores the original scene qpos/link state after solving. IK alone therefore
does not dynamically move the robot. That restoration is another reason to
read measured state only after sending a control target and stepping.

### Unreachable targets still need an answer path

A numerical solver often returns its best candidate when it exhausts samples or
iterations. For an obviously unreachable world target such as `[2, 0, 2] m`,
the candidate may be finite, have the expected shape, and respect joint limits.
Its residual can still be far outside the declared tolerances.

Treating `np.isfinite(q_candidate).all()` as convergence would accept exactly
the case the residual is meant to reject. L05 calls this a **finite best-effort
candidate**, not a successful IK solution.

IK also does not produce a collision-free path. Even a low-residual endpoint
may require a motion that intersects the robot, a table, or an obstacle. L05 has
no obstacles or grasp object; collision-aware planning belongs outside this
lesson.

## Accept the candidate before controlling it

### A layered acceptance rule

For this lab, a candidate is eligible for dynamic execution only when every
enabled condition passes:

1. q has the expected `(9,)` shape and all q/residual values are finite;
2. the returned residual has shape `(6,)`;
3. every solved joint lies inside its runtime position limits;
4. the two finger coordinates remain at the intended values;
5. the norm of the enabled position residual is no greater than the explicit
   position tolerance; and
6. the norm of the enabled rotation-vector residual is no greater than the
   explicit rotation tolerance.

An illustrative pure check is:

```python
position_norm = np.linalg.norm(residual[:3][position_mask])
rotation_norm = np.linalg.norm(residual[3:][rotation_mask])

candidate_valid = bool(
    q_candidate.shape == (9,)
    and residual.shape == (6,)
    and np.isfinite(q_candidate).all()
    and np.isfinite(residual).all()
    and np.all(q_candidate >= lower_limits)
    and np.all(q_candidate <= upper_limits)
    and np.allclose(q_candidate[finger_dofs], q_start[finger_dofs])
    and position_norm <= position_tolerance
    and rotation_norm <= rotation_tolerance
)
```

The code must also handle an empty mask deliberately rather than relying on an
accidental array reduction. In the main experiment, all six task dimensions are
enabled.

### Three errors answer three questions

“Pose error” is too vague unless its stage is named.

| Evidence | How it is obtained | Question answered | What it cannot prove |
|---|---|---|---|
| IK solver residual | returned by `inverse_kinematics(..., return_error=True)` | Did the numerical candidate satisfy the enabled kinematic tolerance? | Did the dynamic robot move there? |
| FK prediction error | FK of `q_candidate` compared with the target | Does an independent kinematic readback agree with the candidate? | Was controller execution adequate? |
| Dynamic tracking error | measured hand pose after control and `scene.step()` | Did the simulated robot approach the target in this finite window? | Is the path collision-free or the task successful? |

The first two may be close but are retained as separately named evidence. The
third includes controller and dynamics behavior and is expected to differ from
an ideal kinematic result.

### The L04 controller remains in the loop

Once a candidate is accepted, L05 does not teleport the robot to it. The loop
uses the same position-controller path as L04:

```python
position_history = [hand.get_pos(relative=False)]
quaternion_history = [hand.get_quat(relative=False)]

for _ in range(180):
    franka.control_dofs_position(q_candidate, dofs_idx_local=all_dofs)
    scene.step()
    if render_enabled:
        wrist_camera.move_to_attach()
    position_history.append(hand.get_pos(relative=False))
    quaternion_history.append(hand.get_quat(relative=False))
```

The teaching experiment requires final position error below `0.02 m`, final
orientation error below `0.05 rad`, and both errors lower than their initial
values. These are operational thresholds for this scene and control window,
not the mechanical accuracy of a Franka robot or a universal IK guarantee.

The full trajectories remain primary evidence. A final value alone can hide
overshoot, late drift, or a long interval spent far from the target.

### Diagnostic execution must remain explicit

The unreachable case is normally rejected before control. The notebook then
offers a clearly labeled **diagnostic override** that may execute only a finite,
in-limit best-effort candidate. Its purpose is to measure what the rejected
candidate would actually do:

- how far the hand moved;
- how much requested position error remains;
- whether the target stayed outside the reachable workspace; and
- why finite output is not equivalent to task success.

The override never changes `ik_valid` to true and never enters the normal
control path. A warning and the original rejection reasons must remain beside
the resulting trace or image.

## Cameras are framed measurements

### Fixed and attached cameras answer different questions

The lab uses two camera relationships:

| Camera | Pose relationship | Primary use |
|---|---|---|
| Fixed world camera | configured `T_WC` remains constant | Observe the whole robot, target marker, and posture change |
| Wrist camera | `T_WC(t) = T_WH(t) T_HC` | Observe how an eye-in-hand view changes with the end effector |

A fixed camera frame can show the scene and final posture. A wrist frame can
show that the sensor viewpoint moved with the hand. Neither image measures IK
residual or task-space tracking error by itself.

### Lifecycle: declare, build, attach, update, render

Both cameras must be created with `scene.add_camera(...)` before
`scene.build()`. Attachment requires the built hand link and therefore happens
after build:

```python
fixed_camera = scene.add_camera(
    res=(640, 360),
    pos=(1.4, -1.4, 1.2),
    lookat=(0.35, 0.0, 0.45),
    fov=42,
    GUI=False,
)
wrist_camera = scene.add_camera(
    res=(640, 360),
    pos=(0.0, 0.0, 1.0),
    lookat=(0.0, 0.0, 0.0),
    fov=42,
    near=0.01,
    far=20.0,
    GUI=False,
)

scene.build()
wrist_camera.attach(hand, offset_T=hand_to_camera_transform)
wrist_camera.move_to_attach()
```

`attach(...)` stores the link and `T_HC` relationship. It does not automatically
refresh the camera after every robot step in Genesis 1.3.3. Call
`move_to_attach()` after the hand moves and before reading the new camera pose or
rendering an observation.

Changing camera topology, render mode, or backend after initialization is not a
supported notebook shortcut. Restart the kernel and rebuild the scene.

### Resolution and vertical field of view

Genesis declares camera resolution as:

```text
res = (width, height)
```

The corresponding single-camera arrays use image-axis order:

```text
RGB shape    = (height, width, 3)
depth shape  = (height, width)
```

Swapping these conventions can pass unnoticed for a square image and fail only
when a non-square sensor is used. The lab deliberately checks the tuple against
the returned arrays.

For the pinhole camera in this lesson, `fov` is the **vertical** field of view.
With width `W`, height `H`, and vertical FOV `theta_v`, Genesis's centered
intrinsic model is:

```text
f_x = f_y = 0.5 H / tan(theta_v / 2)
c_x = W / 2
c_y = H / 2

K = [f_x   0   c_x]
    [ 0   f_y  c_y]
    [ 0    0    1 ]
```

`camera.intrinsics` exposes the 3×3 matrix. These simulated pinhole parameters
are not a claim that the camera has been calibrated against a physical device.
Lens distortion and real hand-eye calibration are outside L05.

### Extrinsics map world coordinates into the camera

`camera.extrinsics` exposes a 4×4 world-to-camera transform for the camera
convention used by Genesis. Keep it paired with the engine's intrinsic and
projection conventions rather than reconstructing axes by guesswork from
`pos` and `lookat`.

For a moving attached camera, the live camera pose is available through
`camera.transform`. In Genesis 1.3.3, `intrinsics` and `extrinsics` are exposed
as cached properties, so code that reads extrinsics before and after a pose
update should derive a fresh world-to-camera matrix from the current transform
using the same version-pinned axis convention:

```python
def live_world_to_camera(camera):
    world_from_graphics_camera = np.asarray(camera.transform, dtype=float)
    graphics_to_camera_axes = np.diag([1.0, -1.0, -1.0, 1.0])
    world_from_camera = world_from_graphics_camera @ graphics_to_camera_axes
    return np.linalg.inv(world_from_camera)
```

This reproduces the pinned `extrinsics` calculation without reusing a value
cached before `move_to_attach()`. The notebook will compare fresh initial and
final world-to-camera matrices; a stale cached property is not evidence that
the wrist camera stayed fixed. This version-specific workaround should be
rechecked when Genesis is upgraded.

The expected relationship is qualitative and structural:

- the fixed camera's transform and extrinsics remain unchanged while the robot
  moves;
- the wrist camera's transform and fresh extrinsics change after
  `move_to_attach()`; and
- `T_WC(t)` remains consistent with the measured hand transform and fixed
  mounting offset.

### RGB and depth have different semantics

With RGB and depth enabled:

```python
rgb, depth, _, _ = fixed_camera.render(
    rgb=True,
    depth=True,
    segmentation=False,
    normal=False,
)
```

The rasterizer depth output is linear metric depth in metres for this path. A
finite depth array can still contain background values at the far plane. The
lab defines valid surface pixels with:

```python
valid_depth = (
    (depth > fixed_camera.near)
    & (depth < fixed_camera.far * (1.0 - 1e-3))
)
```

A valid observation therefore checks more than `np.isfinite(depth).all()`:

- RGB is non-empty `uint8` with shape `(H, W, 3)`;
- depth is floating point with shape `(H, W)`;
- both arrays contain only finite values for this renderer path; and
- at least one depth pixel lies strictly inside the declared clip interval.

The course does not introduce segmentation or point-cloud processing here.
Those outputs need their own label and coordinate contracts rather than being
treated as free extensions of RGB.

### Rendering is an explicit branch

`ROBO_GENESIS_RENDER=0` is the CPU-minimal path. It prints a clear render
`SKIP`, does not create fake RGB/depth arrays, and can plot a diagram derived
from measured hand and link states. Its title must say **measured-state
schematic, not a camera frame**.

`ROBO_GENESIS_RENDER=1` requires the actual Genesis camera path. Camera
creation, rendering, K/extrinsics checks, array validation, or valid-depth
failure stops the run. Catching an error, drawing a Matplotlib substitute, and
still claiming camera verification would erase the distinction the experiment
is designed to teach.

Matplotlib remains useful for displaying Genesis-returned pixels and for
plotting pose/error trajectories. It complements rather than replaces native
simulation views.

## Companion lab: reachable and unreachable poses

The lab keeps the important source-course structure—prediction, a Plane,
Franka, a target marker, a fixed camera, reachable and unreachable targets,
dynamic comparison, checkpoints, and a summary—while adding stricter frame,
quaternion, Jacobian, and camera evidence. It uses built-in primitives only and
does not call the later tabletop/YCB scene builder.

### Predict before running

Write down answers before viewing any output:

1. If IK returns a finite `(9,)` vector, has it necessarily converged?
2. If the IK residual is below tolerance, has the dynamic hand necessarily
   reached the target?
3. What orientation error should be reported for `q_target` and `-q_target`?
4. Which camera transform should remain fixed, and which should change?
5. If `res=(640, 360)`, what RGB and depth shapes should be returned?
6. Can one plausible final image establish low position and orientation error?

The point is not to guess the exact output. It is to make the evidence contract
visible before a result can influence the interpretation.

### Scene and frame inspection

The scene contains a Plane, the bundled Franka, a reachable-target marker, and
a small reference primitive that makes camera motion visually legible. If
rendering is enabled, fixed and wrist cameras are declared before build.

After build, the notebook:

- resolves all nine local DOFs by name and separates seven arm from two finger
  indices;
- obtains the `hand` link and reads its world-frame pose;
- reads q, qdot, joint limits, gains, and force ranges;
- states that W and B coincide only for this scene; and
- attaches and initially updates the wrist camera.

The key Scene, entity, camera, build, attachment, IK, control, sampling, and
validation logic remains directly readable in the notebook. Reusable constants
may come from `robo_genesis`, but the lab is not a black-box wrapper around an
experiment runner.

### Reachable target evidence

The main target is a reachable world-frame hand pose. The target quaternion is
validated as w-x-y-z and normalized before solving. The notebook then:

1. reads the initial hand pose and computes initial position/orientation error;
2. obtains the full `(6, 9)` Jacobian and arm `(6, 7)` slice;
3. solves arm-only IK with `return_error=True`;
4. validates the whole candidate, residual, limits, masks, and fingers;
5. uses FK to predict the hand pose at the candidate;
6. sends the accepted whole-robot q target for 180 outer steps;
7. records measured hand position, quaternion, and joint state after every
   step; and
8. validates final errors and the complete finite trajectories.

With rendering enabled, the lab also captures fixed-camera initial/reached
frames, reached RGB/depth, and initial/final wrist frames. It compares fixed and
fresh wrist extrinsics. With rendering disabled, it uses only the explicitly
labeled measured-state fallback and numerical camera planning information.

### Guided reachable interpretation

The notebook generates four paragraphs from the arrays produced by the current
run rather than embedding expected numbers:

1. **Frames and representation:** identify the target/measured frame, check
   w-x-y-z normalization and `q`/`-q`, and state what is directly comparable.
2. **Solver and FK:** report enabled residual norms, acceptance conditions, FK
   prediction, and finger/limit checks without calling the candidate executed.
3. **Dynamic execution and Jacobian:** compare initial/final position and
   orientation errors, describe their trajectories, and bound the singular
   value statement to the measured configuration.
4. **Camera evidence:** identify fixed versus attached observations, array and
   depth validity, and whether fresh extrinsics changed as expected; if
   rendering was disabled, explicitly state that no camera result was tested.

This ordering prevents an attractive image from becoming the first and only
interpretation of the run.

### Unreachable target evidence

The second target is deliberately far outside the working region. It follows
the same IK and candidate-validation pipeline. The expected *type* of outcome
is rejection on residual, but the notebook derives the actual reasons from the
current arrays rather than printing a hard-coded residual.

Normal control is skipped when `ik_valid` is false. The optional diagnostic
override then executes the finite best-effort candidate under an explicit
warning, records the before/after hand poses, and computes remaining error to
the original requested target. A fixed-camera final frame may show the robot,
but the requested marker can be outside the view; that composition is not an
acceptance test.

The four-part guided interpretation asks:

1. Which exact acceptance conditions failed, and which merely passed?
2. How do reachable and unreachable solver residuals compare component by
   component and by enabled norm?
3. If diagnostic execution occurred, how far did the hand actually move and
   how much requested error remained?
4. Why do finite q, visible motion, and absence of an exception still fail to
   prove reachability, path safety, or task success?

## Four environments and selective updates

The final extension applies the same ideas to `B=4` replicated environments.
It introduces batch shape and per-environment validation, not throughput
benchmarking. Speedup, sampling throughput, and data-recording parallelism are
reserved for L08.

### Preserve the leading dimension

For four environments, the expected shapes are:

| Quantity | Shape |
|---|---:|
| Current whole-robot qpos | `(4, 9)` |
| Target position | `(4, 3)` |
| Target quaternion | `(4, 4)` |
| IK q candidate | `(4, 9)` |
| IK pose residual | `(4, 6)` |
| Measured hand position | `(4, 3)` |

The solver and controller checks operate per row. A small mean error can hide a
failed environment and therefore is not an acceptance rule.

The baseline uses four reachable targets and a shared initial state. After 220
steps, every environment must have finite state, an accepted IK candidate,
position error below the experiment's `0.08 m` threshold, and error lower than
its own initial value. The looser batch threshold is an operational contract for
this extension, not a change to the single-environment pose-quality claim.

### `envs_idx` selects rows, not a new coordinate system

The selective update sends two new targets to environments 1 and 3:

```python
selected_envs = np.asarray([1, 3], dtype=int)
selected_targets = target_positions[selected_envs]

selected_q, selected_residual = franka.inverse_kinematics(
    link=hand,
    pos=selected_targets,
    quat=target_quaternions[selected_envs],
    dofs_idx_local=arm_dofs,
    return_error=True,
    envs_idx=selected_envs,
)
```

Here `selected_targets` has shape `(2, 3)`, and the selected candidate has
shape `(2, 9)`. The number and order of rows must match `envs_idx`. Environments
0 and 2 retain their previous targets while environments 1 and 3 receive new
ones.

“Did not receive a new command” does not mean “frozen.” An untouched
environment still evolves under its previous controller target and the
dynamics. The extension therefore checks:

- selected environments finish within `0.08 m` of their new targets;
- untouched hand displacement stays below `0.005 m`; and
- untouched retained-target error worsens by no more than `0.002 m`.

These thresholds preserve the source exercise's controlled relationship and
must be revalidated on the supported paths. They are not universal properties
of selective control.

### Guided batch interpretation

Read the batch output row by row:

1. verify target, quaternion, candidate, residual, and measured-state shapes;
2. name every environment that passed or failed IK acceptance;
3. compare initial and final errors for each baseline environment rather than
   only their mean; and
4. separate selected-target tracking from untouched motion and retained-target
   error.

A single camera normally shows one rendered environment or viewpoint and cannot
serve as joint evidence for all four rows. The batch extension therefore uses a
per-environment table and a measured target-to-hand plot.

## Evidence boundaries and success criteria

The lesson succeeds only when its evidence remains correctly scoped:

| Observation | Supported conclusion | Unsupported conclusion |
|---|---|---|
| Finite q and correct shape | The solver returned structurally usable data | IK converged |
| Residual below declared tolerances | The candidate passed this kinematic acceptance rule | The robot dynamically reached it |
| FK prediction near target | The candidate's kinematic pose agrees with the target | A controller executed it |
| Measured error decreased in 180 steps | The hand approached the target in this finite window | The path was collision-free or globally stable |
| Valid RGB/depth and K/extrinsics | The configured simulated camera produced a usable observation | The camera is physically calibrated |
| Wrist extrinsics changed after update | The attached viewpoint followed the moving hand | Pixel change proves IK accuracy |
| All four per-env checks passed | This batched experiment met its row-wise contract | Batching always accelerates the workload |

The single-environment thresholds (`0.02 m`, `0.05 rad`) and batch/selective
thresholds are lab acceptance values. They do not describe hardware accuracy,
arbitrary workspaces, other controller gains, or all Genesis backends.

## Common warnings and failures

### The target and measurement use different frames

Print the frame of every pose. Confirm `relative=False` for world-frame link
measurements and check whether a camera quantity requires `T_WC` or `T_CW`.
Never repair a frame mismatch by changing signs until the plot looks plausible.

### The hand rotates unexpectedly

Check whether the target was supplied as w-x-y-z, whether it was normalized,
and whether its axes are expressed in the intended frame. Component-wise
quaternion error can also misdiagnose `q` and `-q`; use the shortest-angle
metric.

### IK returns finite q but the candidate is rejected

This is an expected solver outcome, especially for an unreachable target.
Inspect position and rotation residuals separately, enabled masks, limits, and
finger preservation. Do not loosen tolerances only to make a predetermined
target pass.

### Different initial guesses produce different q

Redundancy makes this possible. Compare each candidate's FK pose, limits,
residual, and distance from the starting configuration. A different valid q is
not automatically an error.

### The Jacobian looks ill-conditioned

Confirm that the seven named arm columns were selected and that the Jacobian
was sampled at the reported configuration. Inspect singular values and try a
nearby starting pose or more damping for diagnosis. Do not call the issue
gimbal lock and do not claim a global workspace result from one matrix.

### FK looks good but dynamic tracking is poor

Check that the candidate entered `control_dofs_position`, that the scene was
stepped for the intended duration, and that measured hand pose was read after
each step. Then inspect joint limits, force saturation, final joint error,
velocity, and the full pose-error trace. FK does not include these execution
effects.

### The unreachable diagnostic seems to move toward the target

A best-effort candidate is expected to reduce some error. Report actual motion
and remaining error. Improvement is not equivalent to satisfying the tolerance,
and it says nothing about path safety.

### RGB width and height appear swapped

Print `camera.res` and both array shapes. `res` is `(W, H)` while arrays are
indexed `(H, W, ...)`. Avoid shape assertions that happen to pass only for a
square test camera.

### Depth is finite but has no useful surface pixels

Apply the declared near/far mask. Far-plane background can be finite. Then
inspect camera pose, clipping planes, and whether geometry lies inside the
view; do not treat the entire finite image as observed surfaces.

### The wrist camera does not move

Confirm that it was added before build, attached to the intended `hand` link
after build, and updated with `move_to_attach()` after the robot moved. Compare
fresh transforms or fresh world-to-camera matrices rather than relying on a
previously cached value.

### Rendering fails

If rendering was requested, preserve the error and fail the render path. Check
the graphics environment, camera declaration order, and clean-kernel settings.
Only an intentionally selected `ROBO_GENESIS_RENDER=0` run may use the labeled
measured-state schematic.

### A selective batch update changes the wrong rows

Print `envs_idx`, target shape, returned q shape, and command shape together.
Check their row order and read every environment after stepping. Remember that
unselected environments continue evolving under previous targets.

### Diagnostic order

Use this dependency order:

```text
version, clean kernel, requested/actual backend, render mode
  → build boundary and camera declaration/attachment
  → frame names, units, quaternion order and norm
  → named arm/finger indices, q shapes, and joint limits
  → IK masks, residuals, and acceptance
  → FK prediction
  → controller command, step count, and measured pose trajectory
  → local Jacobian evidence
  → live camera pose, K/extrinsics, RGB/depth, and clip mask
  → batch leading dimension and per-environment relationships
```

This order catches structural mistakes before they are misdiagnosed as IK
tuning or renderer behavior. Genesis MJCF importer warnings may be recorded and
explained, but they do not excuse wrong shapes, non-finite values, limit
violations, or a failed requested render.

## Checkpoints and exercises

### Concept checkpoints

Answer these without looking back at the tables:

1. What does `T_AB` do, and how is `T_BA` related to it?
2. Why can world and robot-base frames coincide in this scene but not in
   general?
3. Why are w-x-y-z order, normalization, and `q`/`-q` equivalence three
   separate checks?
4. What is the difference between FK and dynamic execution of an FK/IK
   candidate?
5. Why is the Franka arm redundant for a six-dimensional hand-pose task?
6. What does a small Jacobian singular value mean locally, and why is it not
   Euler gimbal lock?
7. What role does damping play in a least-squares IK update?
8. Why can a finite, in-limit q still fail IK acceptance?
9. What are the six components of Genesis's returned IK error?
10. Which evidence distinguishes solver residual, FK prediction error, and
    dynamic tracking error?
11. Why must an attached camera call `move_to_attach()` after motion?
12. How do `res=(W,H)` and RGB `(H,W,3)` describe the same camera?
13. Why is a finite far-plane depth value not necessarily a measured surface?
14. Why can a batch mean conceal a failed environment?
15. Why can an environment that receives no new selective command still move?

### Hands-on exercise

Run the reachable and unreachable experiments from a clean kernel. Then:

1. draw a frame chain for W, B, H, and both cameras, and label every target and
   measured pose used in an error calculation;
2. verify the target quaternion norm and show numerically that changing its sign
   leaves the shortest-angle error unchanged;
3. report full and arm Jacobian shapes and the singular values at the measured
   configuration without assigning a universal singularity threshold;
4. list every IK acceptance condition and its current pass/fail result;
5. compare solver residual, FK prediction error, initial execution error, and
   final execution error with units;
6. explain the unreachable case using rejection reasons, diagnostic motion, and
   remaining error rather than only an image;
7. when rendering is enabled, verify fixed/wrist transform behavior, K,
   RGB/depth shapes and dtypes, and valid depth; otherwise identify every camera
   check that was skipped; and
8. for B=4, report every row's baseline and selective-update results and show
   why an aggregate mean is insufficient.

As an extension, keep the target fixed but change only the IK initial guess to
another valid arm posture. Compare candidate q, FK pose, residual, and distance
from the original q. The point is to observe redundancy and numerical search,
not to rank one posture as universally best.

Do not extend the scene with a table, YCB object, grasp action, or collision
planner. Those additions change the question and belong to later lessons.

## Summary and connections

- A pose is position plus orientation in a named frame. This lesson uses
  world-frame hand targets and Genesis's w-x-y-z unit quaternions.
- `q` and `-q` represent the same rotation; shortest-angle quaternion error
  prevents a representation sign from becoming a false physical error.
- FK maps q to a world-frame link pose. The Jacobian maps joint velocity to
  local hand spatial velocity, and its singular values describe only the
  current configuration.
- A seven-DOF arm solving a six-dimensional pose task is redundant. IK can be
  non-unique and depends on its initial guess, masks, damping, and limits.
- Damped least squares regularizes a local solve but cannot make an unreachable
  target reachable or produce a collision-free path.
- A finite solver output is a candidate. Accept it only after shape,
  finiteness, limit, finger, and enabled residual checks.
- Solver residual, FK prediction, and dynamic tracking are different evidence.
  The accepted target still needs L04's controller and `scene.step()`.
- A fixed camera holds its world pose. A wrist camera composes the measured hand
  pose with a fixed mount and must be refreshed after motion.
- Genesis uses `res=(W,H)` and image arrays ordered `(H,W,...)`; vertical FOV,
  K, world-to-camera extrinsics, near/far, and valid depth all belong to the
  observation contract.
- Batched IK preserves a leading environment dimension. Selective commands and
  acceptance must be checked per environment, not hidden in a mean.

L06 will place these frame and camera contracts into a tabletop task scene with
approved objects. L07 will sequence pose targets into a scripted expert and
must add motion and grasp logic rather than treating IK as path planning. L08
will revisit batched environments for throughput, synchronized observations,
and data recording. None of those later claims is established by one L05 pose
reach.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned FK, Jacobian, inverse-kinematics, state, and control API
  behavior.
- [Genesis 1.3.3 inverse-kinematics solver source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/solvers/rigid/abd/inverse_kinematics.py)
  — damped least-squares update, masks, tolerances, limits, and best-candidate
  behavior.
- [Genesis 1.3.3 `Camera` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — resolution/FOV, transform, intrinsic/extrinsic, attachment, render, depth,
  and clipping semantics.
- [Genesis 1.3.3 bundled Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — the robot model, joints, ranges, and actuator configuration used by this
  lesson.
- [Modern Robotics, Lynch and Park](https://modernrobotics.northwestern.edu/nu-gm-book-resource/)
  — open textbook background for frames, rigid transforms, forward and inverse
  kinematics, Jacobians, redundancy, and singularities.
- [OpenCV camera calibration and 3D reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
  — reference for the pinhole intrinsic/extrinsic projection model and camera
  coordinate terminology; Genesis-specific conventions remain defined by the
  pinned Genesis source above.
