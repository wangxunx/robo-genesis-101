---
lesson: L05
slug: inverse-kinematics-end-effector-poses-and-cameras
locale: en
title: "Inverse Kinematics, End-Effector Poses, and Cameras"
duration_minutes: 120
hardware: cpu-ok
status: cpu-verified
---

# L05 · Inverse Kinematics, End-Effector Poses, and Cameras

> **Course status:** L05 is being revised and is not yet published. The revised
> bilingual lecture and notebook must be reviewed and run again before their
> runtime status is reaffirmed.

## Where this lesson fits

L04 started with a joint target and followed it through position control,
actuator limits, dynamics, and `scene.step()`. This lesson asks where that joint
target can come from when the task is stated in Cartesian space:

> Given the Franka joint configuration, how do we find the hand pose? Given a
> desired hand pose, how do we find and validate a joint target, execute it
> through the L04 controller, and measure what actually happened?

These are the forward-kinematics (FK) and inverse-kinematics (IK) questions.
They connect joint space to the pose of the robot's end effector. A short final
section adds one fixed camera so that the same scene can also produce RGB and
depth observations.

The complete lesson follows three small chains:

```text
current q  ──FK──>  current end-effector pose

target end-effector pose  ──IK + residual check──>  q goal
q goal  ──L04 position control + scene.step()──>  measured end-effector pose

current scene state  ──fixed camera──>  RGB + depth
```

Keep the arrows separate. FK predicts a pose; it does not move the robot. IK
returns a joint candidate; it does not execute a controller. A camera image
shows the scene; it does not prove that a numerical tolerance was met.

Before starting, you should be able to:

- explain the `init → declare → build → step/read` lifecycle;
- identify Franka's seven arm DOFs and two finger DOFs;
- distinguish a state reset from a position-control target; and
- check array shapes, units, and finite values.

No table, grasp object, state machine, dataset, or learned policy is needed.
L06 will add the grasping scene after this joint-space/task-space connection is
clear.

### A 120-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–10 min | Reconnect L04 control to task-space targets | Draw the q, pose, controller, and camera chain |
| 10–25 min | Hand link, world-frame pose, and `wxyz` quaternion | Read the target pose without mixing frames or quaternion order |
| 25–42 min | Forward kinematics | Explain what pose a given q predicts |
| 42–62 min | Inverse kinematics and residuals | Decide whether a returned candidate is acceptable |
| 62–88 min | IK → FK prediction → dynamic execution | Compare target, predicted, and measured poses |
| 88–100 min | One fixed camera | Obtain RGB/depth and check their shapes |
| 100–112 min | Unreachable target | Reject a finite best-effort candidate using its residual |
| 112–120 min | Checkpoint, exercise, and L06 handoff | Restate the evidence chain and its limits |

## Learning objectives

By the end of L05, you should be able to:

1. describe an end-effector pose as position plus orientation in a named frame,
   and recognize Genesis's w-x-y-z quaternion order;
2. use `q → FK → pose` to predict the Franka hand pose, while explaining why an
   FK calculation does not move the dynamic scene;
3. use `target pose → IK → q candidate`, read the six-dimensional IK residual,
   and avoid treating a finite q as proof of convergence;
4. send an accepted q through the L04 position-control loop and distinguish IK
   residual, FK prediction error, and measured execution error;
5. reject an obviously unreachable target without sending its candidate to the
   controller; and
6. add one fixed camera, render RGB and depth, and relate `res=(W, H)` to the
   returned `(H, W, 3)` and `(H, W)` arrays.

## End-effector poses

### The hand link is the end effector in this lesson

A robot model contains many links. L05 uses Franka's `hand` link as its end
effector:

```python
hand = franka.get_link("hand")
```

An end-effector pose combines:

```text
position     [x, y, z]       metres
orientation  [w, x, y, z]    unit quaternion
```

The numbers are meaningful only with a reference frame. In this simple fixed-
base scene, the target position, target orientation, and measured hand pose are
all expressed in the world frame. Genesis makes the requested measurement
explicit:

```python
measured_position = hand.get_pos(relative=False)
measured_quaternion = hand.get_quat(relative=False)
```

`relative=False` requests the world-frame link pose. Therefore the measured
position can be compared directly with a world-frame target position. If one
quantity were expressed in a camera or moving-base frame, direct subtraction
would be invalid.

The Franka base happens to coincide with the world frame in this notebook
because the robot uses its default fixed pose. That is a property of this
scene, not a general identity.

### Genesis uses w-x-y-z quaternion order

The target orientation in the lab is:

```python
target_quaternion = np.array([0.0, 1.0, 0.0, 0.0])  # w, x, y, z
```

Some libraries use x-y-z-w. Copying between conventions without reordering
changes the rotation. A quaternion must also have unit norm. The notebook uses
a small helper that checks shape and finiteness before normalizing minor
floating-point drift:

```python
def normalize_wxyz(quaternion):
    quaternion = np.asarray(quaternion, dtype=float)
    if quaternion.shape != (4,) or not np.isfinite(quaternion).all():
        raise ValueError("expected a finite wxyz quaternion with shape (4,)")
    norm = np.linalg.norm(quaternion)
    if norm < 1e-12:
        raise ValueError("a zero quaternion does not define an orientation")
    return quaternion / norm
```

Unit quaternions `q` and `-q` describe the same physical rotation. An
orientation error must therefore ignore this sign choice. For normalized
quaternions, the shortest angular error is:

```python
def quaternion_angle_error(measured_wxyz, target_wxyz):
    measured = normalize_wxyz(measured_wxyz)
    target = normalize_wxyz(target_wxyz)
    cosine_half_angle = np.clip(abs(np.dot(measured, target)), 0.0, 1.0)
    return float(2.0 * np.arccos(cosine_half_angle))
```

This is the only quaternion calculation the main experiment needs. The lesson
does not require Euler angles or a general coordinate-transform derivation.

## Forward kinematics: q to pose

Forward kinematics answers:

> If the robot has joint configuration q, where is its end effector and how is
> it oriented?

For the hand link, write the mapping as:

```text
q  ──FK──>  (hand position, hand orientation)
```

This mapping is deterministic for a fixed robot model. It is a calculation,
not a command. Calling FK for a candidate q does not change the current q,
apply actuator effort, advance simulation time, or prove that the controller
can track that candidate.

Genesis can predict the hand pose for a supplied q with:

```python
fk_positions, fk_quaternions = franka.forward_kinematics(
    q_candidate_raw,
    links_idx_local=[hand.idx_local],
)
predicted_position = to_numpy(fk_positions).reshape(3)
predicted_quaternion = to_numpy(fk_quaternions).reshape(4)
```

The returned values are the world-frame pose of the requested link. They can
be compared with the world-frame target pose before any control command is
sent.

::: warning Genesis 1.3.3 call order
In the pinned Genesis version, `forward_kinematics()` currently reuses scratch
storage initialized by the first IK call. The companion notebook therefore
explains FK first but calls it immediately after the first IK solve. This is a
version-specific API lifecycle detail, not a mathematical dependency of FK on
IK.
:::

## Inverse kinematics: pose to q

Inverse kinematics asks the opposite question:

> Which joint configuration could place the end effector at a desired pose?

```text
target hand pose  ──IK──>  one q candidate
```

The word “one” matters. Franka has seven arm joints for a six-dimensional hand
pose, and numerical IK can produce different valid configurations from
different starting postures. L05 does not try to enumerate every solution or
derive the solver. It needs only three practical facts:

- IK is a numerical search, not a direct guarantee;
- joint limits and the initial configuration affect the result; and
- the returned residual tells us whether the candidate met the requested pose
  tolerance.

### Read the candidate and residual together

The main solve uses the seven arm DOFs while leaving the fingers in their
current state:

```python
q_candidate_raw, ik_error_raw = franka.inverse_kinematics(
    link=hand,
    pos=target_position,
    quat=target_quaternion,
    init_qpos=q_start,
    dofs_idx_local=arm_dofs,
    respect_joint_limit=True,
    pos_tol=position_tolerance,
    rot_tol=rotation_tolerance,
    return_error=True,
)
```

For this unbatched Franka, Genesis returns a whole-entity q candidate with
shape `(9,)` and an error vector with shape `(6,)`:

```text
ik_error[:3]  position residual vector, metres
ik_error[3:]  rotation residual vector, radians
```

The lab reduces each vector to an L2 norm and checks it against the explicit
tolerance:

```python
q_candidate = to_numpy(q_candidate_raw).reshape(-1)
ik_error = to_numpy(ik_error_raw).reshape(-1)

position_residual = float(np.linalg.norm(ik_error[:3]))
rotation_residual = float(np.linalg.norm(ik_error[3:]))

ik_valid = bool(
    q_candidate.shape == (9,)
    and ik_error.shape == (6,)
    and np.isfinite(q_candidate).all()
    and np.isfinite(ik_error).all()
    and position_residual <= position_tolerance
    and rotation_residual <= rotation_tolerance
)
```

The pinned Genesis defaults are `5e-4 m` for position and `5e-3 rad` for
rotation. The notebook passes them explicitly so the acceptance rule is
visible.

The shape and finite checks are necessary, but they are not sufficient. An
unreachable target can still return a finite best-effort q. Only the residual
reveals that the target tolerance was not met.

### IK is not motion planning

IK produces an endpoint configuration. It does not produce a collision-free
trajectory to that endpoint. The L05 scene intentionally contains only a
plane, Franka, and a non-colliding target marker. L06 and L07 will add task
geometry and safe waypoint logic; a low L05 residual must not be described as
a successful grasp or a safe path.

## Solve, predict, execute, and measure

The reachable experiment uses the world-frame target from the source course:

```python
target_position = np.array([0.45, 0.0, 0.35])
target_quaternion = normalize_wxyz([0.0, 1.0, 0.0, 0.0])
```

It then follows four stages in order.

### 1. Solve IK

Call `inverse_kinematics(..., return_error=True)` and apply the visible
acceptance rule. If either residual exceeds its tolerance, stop before the
controller.

### 2. Predict with FK

Call `forward_kinematics()` for the accepted q candidate and compare its
predicted hand pose with the target. This checks what the candidate means
kinematically. It still does not move the simulated robot.

### 3. Execute through the L04 controller

Use the same dynamic path established in L04:

```python
for _ in range(180):
    franka.control_dofs_position(q_candidate)
    scene.step()
```

Do not replace the loop with `set_dofs_position(q_candidate)`. That would
teleport the state and remove the controller and dynamics from the experiment.

The notebook samples the hand position and orientation after each step. A
short error plot shows whether the measured pose approached the target during
the finite control window.

### 4. Measure the resulting pose

After stepping, read the world-frame hand pose and compute position and
orientation errors:

```python
measured_position = to_numpy(hand.get_pos(relative=False)).reshape(3)
measured_quaternion = to_numpy(hand.get_quat(relative=False)).reshape(4)

position_error = float(np.linalg.norm(measured_position - target_position))
orientation_error = quaternion_angle_error(
    measured_quaternion,
    target_quaternion,
)
```

The lab uses operational thresholds of `<0.02 m` position error and
`<0.05 rad` orientation error for this scene, controller configuration, and
180-step window. These values are not claims about real Franka accuracy or all
possible targets.

### Three measurements answer three questions

| Evidence | Question answered | What it does not prove |
|---|---|---|
| IK residual | Did the numerical candidate satisfy the pose tolerance? | Did the robot move? |
| FK prediction error | What hand pose does this q kinematically predict? | Did the controller track q? |
| Measured execution error | Where did the dynamic hand end after stepping? | Was the path collision-free or a grasp successful? |

Keeping these names explicit is more useful than building a large validation
framework around them.

## A fixed camera, briefly

The camera is a small bridge to later visual observations, not the main topic
of L05. The notebook uses one fixed, world-view camera. Like every Scene
component, it must be declared before `scene.build()`:

```python
camera = scene.add_camera(
    res=(640, 360),
    pos=(1.2, -1.2, 1.0),
    lookat=(0.35, 0.0, 0.35),
    fov=45,
    GUI=False,
)
scene.build()
```

`pos` and `lookat` are world-frame points. `fov` controls how wide the view is.
This lesson does not derive the pinhole model, inspect camera intrinsics or
extrinsics, attach a wrist camera, or discuss calibration.

### RGB and depth

When rendering is enabled, one call returns the two observations used here:

```python
rgb, depth, _, _ = camera.render(rgb=True, depth=True)
rgb = to_numpy(rgb)
depth = to_numpy(depth)
```

Genesis declares `res=(width, height)`, while image arrays are indexed by row
before column:

```text
camera res:  (W, H)
RGB shape:   (H, W, 3)
depth shape: (H, W)
```

For `res=(640, 360)`, the expected shapes are `(360, 640, 3)` and
`(360, 640)`. RGB contains color values; depth contains simulated distance
values for the renderer path. The notebook checks shape, basic dtype, and
finiteness, then displays one RGB/depth pair.

Rendering is optional for the CPU-minimal FK/IK path. With
`ROBO_GENESIS_RENDER=0`, the notebook prints a clear `SKIP` and does not create
fake camera arrays or a substitute image. With `ROBO_GENESIS_RENDER=1`, a
camera failure is a real failure of the requested path.

The image can show the robot, marker, and final posture. Numerical IK residual
and execution error must still come from the solver and measured state.

## Companion lab

The notebook deliberately stays close to the source Module 04 experiment. It
contains one Scene, one reachable target, one fixed camera, and one unreachable
negative case.

### Predict before running

Write down answers before executing the notebook:

1. If IK returns a finite `(9,)` q, has it necessarily converged?
2. Does calling FK for `q_candidate` move the robot?
3. If the IK residual is small, has the dynamic hand necessarily reached the
   target?
4. For `res=(640, 360)`, what RGB and depth shapes do you expect?

### Run the reachable case

The notebook:

1. initializes the selected backend and optional render branch;
2. declares a Plane, Franka, target marker, and optional fixed camera;
3. builds the Scene and reads the initial q and world-frame hand pose;
4. solves IK for the reachable target and checks both residual norms;
5. uses FK to predict the candidate hand pose;
6. executes the accepted q for 180 steps through position control;
7. reads the measured hand pose and plots a concise error history; and
8. renders one RGB/depth pair when requested.

The printed output should let you trace target pose → IK candidate → FK
prediction → controller → measured pose without searching through helper
tables or generated prose.

### Reject the unreachable case

The second target is deliberately far away:

```python
unreachable_position = np.array([2.0, 0.0, 2.0])
```

Run the same IK call and the same residual check. Genesis may return a finite q,
but the position or rotation residual should exceed tolerance. The normal
result is therefore:

```text
IK valid: no
command sent: no
```

Do not execute the rejected candidate. The negative case has already shown the
important fact: a returned q is a candidate, and the residual decides whether
it satisfied this pose request.

## Common failures and a short diagnostic order

### The hand orientation is unexpected

Check that the target uses w-x-y-z order, has unit norm, and is expressed in the
same world frame as the measured hand pose. Do not fix the result by swapping
components until the picture looks plausible.

### FK appears to move the robot

Check the surrounding code. FK itself is a calculation. A later controller
command, state reset, or `scene.step()` changed the dynamic state.

### IK returns a finite q but `ik_valid` is false

This is expected for a best-effort solution. Inspect position and rotation
residuals separately. Do not loosen tolerances only to force an unreachable
target to pass.

### FK prediction is accurate but execution error is large

Confirm that the accepted q entered `control_dofs_position()`, the scene was
stepped for the intended duration, and the measured pose was read afterward.
Then inspect the error history and joint tracking. FK does not include dynamic
tracking.

### RGB width and height seem reversed

Remember that camera configuration uses `(W, H)`, while arrays use
`(H, W, ...)`. Print `camera.res`, `rgb.shape`, and `depth.shape` together.

### Rendering fails

If rendering was requested, preserve the error and check the graphics
environment and build order. If rendering was intentionally disabled, report
only the numerical FK/IK path and the explicit camera `SKIP`.

Use this diagnostic order:

```text
version, backend, and render mode
  → build boundary and hand link
  → world frame, units, and quaternion order
  → q and residual shapes
  → IK residual and acceptance
  → FK prediction
  → controller, step count, and measured pose
  → optional RGB/depth shapes
```

## Checkpoints and exercise

### Concept checkpoints

Answer these without looking back:

1. What are the inputs and outputs of FK?
2. What are the inputs and outputs of IK?
3. Why does a finite q not prove that IK converged?
4. What is the difference between an IK residual and measured execution error?
5. Why does an FK prediction not prove that the controller executed q?
6. Why must target and measured poses use the same reference frame?
7. What quaternion component order does Genesis use?
8. What RGB/depth shapes correspond to `res=(640, 360)`?

### Hands-on exercise

After the baseline succeeds, change only the reachable target x coordinate by
`+0.03 m` while keeping its orientation unchanged.

Before running, predict whether the target remains reachable. Then report:

1. the IK position and rotation residuals;
2. the FK-predicted position and orientation errors;
3. the final measured position and orientation errors after 180 steps; and
4. whether the camera shape contract changed.

Explain any difference between FK prediction and measured execution using the
controller and finite observation window. Do not add a table, object, grasp,
batch dimension, or new camera; those changes would create a different lesson.

## Summary and connections

- An end-effector pose is position plus orientation in a named frame. L05 uses
  world-frame hand poses and Genesis's w-x-y-z quaternion order.
- FK maps q to a predicted hand pose. It does not move the robot.
- IK maps a target pose to one q candidate. Shape and finiteness are not enough;
  position and rotation residuals decide whether this request passed.
- An accepted candidate still needs L04 position control and repeated
  `scene.step()` calls. Measure the resulting hand pose after execution.
- IK residual, FK prediction, and measured execution error answer different
  questions.
- An unreachable target may still return a finite best-effort q. Reject it and
  do not send it to the controller.
- One fixed camera provides RGB and depth. `res=(W, H)` corresponds to RGB
  `(H, W, 3)` and depth `(H, W)`.

L06 will place this controlled robot into a tabletop grasping scene. L07 will
sequence multiple pose targets into a scripted expert. Neither lesson should
treat IK as a collision-free path planner or a low residual as grasp success.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned FK, IK, link-state, and control API behavior.
- [Genesis 1.3.3 `Camera` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — version-pinned camera declaration, resolution, rendering, and depth
  behavior.
- [Genesis 1.3.3 bundled Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — the robot model, joints, limits, and actuator configuration used here.
- [Modern Robotics, Lynch and Park](https://modernrobotics.northwestern.edu/nu-gm-book-resource/)
  — open textbook background for frames, forward kinematics, inverse
  kinematics, and robot motion.
