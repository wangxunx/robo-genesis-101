---
lesson: L04
slug: robot-models-dofs-and-joint-control
locale: en
title: "Robot Models, Degrees of Freedom, and Joint Control"
duration_minutes: 90
hardware: cpu-ok
status: cpu-verified
---

# L04 · Robot Models, Degrees of Freedom, and Joint Control

> **Course status:** the lecture and executable notebook are available. The
> notebook has passed clean-kernel verification on CPU and on the reference AMD
> ROCm platform, including the Genesis camera path. L04 is `cpu-verified`
> because CPU remains its minimum hardware contract.

## Where this lesson fits

L02 introduced the Genesis lifecycle and the hierarchy from a Scene to rigid
entities and links. L03 then showed that one call to `scene.step()` advances the
outer timestep `dt`, and that a final image is not enough evidence for a
physical claim. L04 applies both ideas to the course's first articulated robot:
the Franka Emika Panda.

The central question is:

**How does a name in a robot model become the correct control dimension, and
how does a position target become measured motion through a controller,
actuator limits, and simulated dynamics?**

The answer is not “assign the target and read it back.” A useful trace is:

```text
MJCF link and joint names
          ↓
runtime entity-local DOF indices
          ↓
initial q + target q + KP/KV + force range
          ↓
target command → controller → dynamics → scene.step()
          ↓
measured q(t), qdot(t), control force(t), and robot posture
          ↓
rise, overshoot, settling, final error, and saturation evidence
```

Before starting, you should be able to:

- explain `gs.init → Scene → add_entity/add_camera → build → step/read/render`;
- distinguish an Entity from one of its rigid Links;
- calculate step count and simulated duration from the outer `dt`;
- inspect NumPy array shape, units, and finiteness; and
- compare cases by changing one factor while holding the others fixed.

You do not need forward or inverse kinematics, end-effector frames, camera
calibration, grasping, or policy learning. L05 will introduce those topics only
after this lesson establishes how joint targets are executed.

## Learning objectives

By the end of L04, you should be able to:

1. explain the runtime relationship among an MJCF model, Entity, Link, Joint,
   degree of freedom (DOF), and generalized position (`qpos`);
2. explain why the fixed-base Franka used here has seven arm joints but nine
   controlled dimensions, then classify their units and limits;
3. resolve entity-local DOF indices from joint names and verify that command,
   state, gain, and limit arrays have compatible shapes;
4. distinguish `set_dofs_position(...)` as a state reset from
   `control_dofs_position(...)` as a dynamic control target, and place both on
   the correct side of the build boundary;
5. use a bounded PD model to reason about KP, KV, effective inertia, gravity,
   discrete time, and force-range saturation without claiming a universal
   tuning recipe;
6. design and interpret a joint4 step experiment using posture, position,
   velocity, control-force, and step-response metrics together; and
7. diagnose name, index, shape, unit, limit, non-finite-state, saturation,
   settling, and rendering failures in a systematic order.

## From an MJCF file to a controllable system

### What the model contributes

The lab loads Genesis's bundled Franka model with:

```python
from robo_genesis.scene_config import FRANKA_MJCF

franka = scene.add_entity(
    gs.morphs.MJCF(file=FRANKA_MJCF),
)
```

MJCF is MuJoCo's XML-based model definition format. In this model it
describes, among other things:

- a tree of bodies and their visual and collision geometry;
- inertial properties for the rigid bodies;
- joints, joint axes, and position ranges;
- actuators and their gains, biases, and force ranges; and
- equality and tendon relationships for the two gripper fingers.

The XML is a declaration, not yet a simulated trajectory. `add_entity(...)`
returns the Franka Entity handle during scene declaration. `scene.build()` then
imports the model and creates the solver state. Joint-state getters and control
calls are runtime operations and therefore belong after build.

Genesis currently treats the bundled MJCF as one rigid Entity. That Entity
contains multiple Links connected by the model's movable relationships. This
extends the L02 hierarchy:

```text
Scene
└── Franka RigidEntity
    ├── rigid Links: link0, link1, ..., hand, fingers
    ├── Joints: joint1, ..., joint7, finger joints
    └── DOFs and qpos coordinates owned by those joints
```

A Link is a rigid body with pose, inertia, and geometry. A Joint constrains the
relative motion between a child Link and its parent. A DOF is one independent
scalar motion axis admitted by that constraint. These are different kinds of
objects; a Link number, Joint number, and DOF index are not interchangeable.

### Fixed, revolute, and prismatic relationships

Three relationship types are sufficient for this lesson:

| Type | Allowed relative motion | DOFs | Position unit | Effort unit |
|---|---|---:|---|---|
| Fixed | none | 0 | none | none |
| Revolute | rotation about one axis | 1 | rad | N·m |
| Prismatic | translation along one axis | 1 | m | N |

A fixed relationship contributes no control coordinate. In the bundled model,
the bodies without a movable joint remain rigidly attached through the model
tree, and the robot base is fixed to the world. The seven arm joints are
revolute. The two finger joints are prismatic and each moves over the model's
`0` to `0.04 m` range.

Do not generalize “one joint equals one DOF.” A spherical joint can have three
rotational DOFs, while a free joint has six velocity DOFs. Conversely, a fixed
relationship has none.

### DOF and `qpos` answer different questions

A DOF counts independent instantaneous motion axes. `qpos` stores generalized
coordinates used to describe configuration. Their dimensions need not match:

- a one-axis revolute or prismatic joint normally has one DOF and one `qpos`;
- a spherical orientation has three DOFs but is often represented by a
  four-component unit quaternion; and
- a free rigid body has six DOFs but can use seven position coordinates: three
  for translation and four for quaternion orientation.

The fixed-base Franka in this lesson is a convenient special case. Every
movable joint is one-axis, so the runtime model has nine DOFs and nine `qpos`
coordinates. That equality is a property of this model, not an API invariant.
With Genesis 1.3.3, the expected runtime summary for this pinned import is 11
Links, 9 movable Joints, 9 DOFs, and 9 `qpos` coordinates; the notebook checks
those counts rather than relying on the statement alone.

Genesis exposes the distinction on each `RigidJoint`:

```python
joint = franka.get_joint("joint4")
print(joint.n_dofs)
print(joint.n_qs)
print(joint.dofs_idx_local)
print(joint.qs_idx_local)
```

Code should inspect these properties rather than infer them from the joint's
position in `franka.joints`.

## Franka's seven arm DOFs and two finger DOFs

The model-specific control map is:

| Joint names | Count | Joint type | Position / velocity | Control effort |
|---|---:|---|---|---|
| `joint1`–`joint7` | 7 | revolute | rad / rad·s⁻¹ | N·m |
| `finger_joint1`, `finger_joint2` | 2 | prismatic | m / m·s⁻¹ | N |

The phrase “7-DOF Franka arm” describes the arm chain. It does not include the
two independently represented finger DOFs. A whole-robot array in this course
therefore has length nine, while an arm-only array has length seven.

The bundled model gives the following position ranges:

| Local DOF | Joint | Position range | Unit |
|---:|---|---:|---|
| 0 | `joint1` | `[-2.8973, 2.8973]` | rad |
| 1 | `joint2` | `[-1.7628, 1.7628]` | rad |
| 2 | `joint3` | `[-2.8973, 2.8973]` | rad |
| 3 | `joint4` | `[-3.0718, -0.0698]` | rad |
| 4 | `joint5` | `[-2.8973, 2.8973]` | rad |
| 5 | `joint6` | `[-0.0175, 3.7525]` | rad |
| 6 | `joint7` | `[-2.8973, 2.8973]` | rad |
| 7 | `finger_joint1` | `[0, 0.04]` | m |
| 8 | `finger_joint2` | `[0, 0.04]` | m |

These values are versioned model data, not universal mechanical specifications
for every Franka asset. Read them from the runtime object in executable work:

```python
lower, upper = franka.get_dofs_limit(dofs_idx_local=all_dofs)
```

This check catches model changes and prevents an apparently valid nine-element
target from commanding an invalid position.

## Resolve indices by name

### Why bare indices are fragile

Writing “joint4 is index 3” is true for the exact imported model used here, but
it is a poor discovery mechanism. Another asset can add a floating base,
reorder joints, or represent a gripper differently. A robust program resolves
the mapping once by name and then verifies it.

```python
import numpy as np

joint_names = [f"joint{i}" for i in range(1, 8)] + [
    "finger_joint1",
    "finger_joint2",
]

dof_indices = []
for name in joint_names:
    joint = franka.get_joint(name)
    if joint.n_dofs != 1 or joint.n_qs != 1:
        raise ValueError(
            f"{name} must be one-DOF/one-qpos in this lab, got "
            f"n_dofs={joint.n_dofs}, n_qs={joint.n_qs}"
        )
    dof_indices.extend(joint.dofs_idx_local)

all_dofs = np.asarray(dof_indices, dtype=int)
arm_dofs = all_dofs[:7]
finger_dofs = all_dofs[7:]

assert all_dofs.shape == (9,)
assert np.unique(all_dofs).size == 9
```

`dofs_idx_local` is explicitly local to the Franka Entity. Genesis also has
solver-level indices, and a Joint has its own list position. Passing one index
space where another is expected can control the wrong dimension or fail only
after the scene becomes more complex.

### Shape is part of the interface

For an unbatched scene, these calls should produce one value per requested DOF:

```python
q = franka.get_dofs_position(dofs_idx_local=all_dofs)
qdot = franka.get_dofs_velocity(dofs_idx_local=all_dofs)
lower, upper = franka.get_dofs_limit(dofs_idx_local=all_dofs)

assert tuple(q.shape) == (9,)
assert tuple(qdot.shape) == (9,)
assert tuple(lower.shape) == (9,)
assert tuple(upper.shape) == (9,)
```

The course notebook converts tensors to NumPy before analysis and checks that
every value is finite. A nine-element vector with the wrong units is still
wrong, so the structure table must keep joint type and unit beside each index.

For a batched scene, an environment dimension is added. L04 deliberately uses
one unbatched robot so that model mapping and control evidence remain visible;
parallel environment shapes belong later in the learning pipeline.

## State reset is not dynamic control

Two APIs that both accept positions have different meanings.

### `set_dofs_position(...)` establishes state

```python
franka.set_dofs_position(
    q_start,
    dofs_idx_local=all_dofs,
    zero_velocity=True,
)
```

This directly assigns the selected generalized positions. With
`zero_velocity=True`, it also clears their velocity. That is useful for putting
every experimental case at the same initial condition.

It is not evidence that the controller moved the robot. Using this call for
every point of a desired path would overwrite state rather than demonstrate
actuator-limited motion through the dynamics.

### `control_dofs_position(...)` establishes a target

```python
franka.control_dofs_position(
    q_target,
    dofs_idx_local=all_dofs,
)
scene.step()
q_measured = franka.get_dofs_position(dofs_idx_local=all_dofs)
```

This configures a position-controller target. The measured state generally
does not jump to the target. The controller computes an effort, the simulator
advances one outer timestep, and only then does the program observe a new
position and velocity.

The distinction is the basis of a fair gain experiment:

1. reset every case to the same `q_start` and zero velocity;
2. configure gains and force limits;
3. send a target;
4. step the dynamics; and
5. measure the response.

## Three control modes, one main experiment

Genesis 1.3.3 exposes three relevant control calls:

| Call | Command meaning | Typical selected-DOF unit | What it is not |
|---|---|---|---|
| `control_dofs_position` | target generalized position | rad or m | direct state assignment |
| `control_dofs_velocity` | target generalized velocity | rad/s or m/s | a position target |
| `control_dofs_force` | commanded generalized effort | N·m or N | a target that guarantees a pose |

Position mode uses the configured positional gain and velocity damping;
velocity mode uses its velocity-control setting. Force mode sends generalized
effort directly and therefore asks the caller to manage more of the dynamics
and safety reasoning.

L04 explains the interface boundary for all three modes, but its executable
experiment uses only position control. Holding the control mode fixed is
necessary for the KP/KV comparison. Velocity and force-control experiments
would introduce different questions and are not hidden extra baselines.

## The outer-step control loop

L03 defined `dt` as the time advanced by one `scene.step()`. It now also becomes
the straightforward Python command and observation cadence:

```text
at t[k]: choose or repeat q_target[k]
         ↓
controller computes a bounded effort from target and state
         ↓
scene.step() advances the dynamics by dt
         ↓
at t[k+1]: read q, qdot, and control effort
```

The lab uses `dt = 0.01 s`. A 1.2-second observation window therefore contains
120 outer steps. Record the initial position at `t = 0` before the first step,
then record new state after each step. This produces 121 position samples,
including both endpoints. Quantities read only after a step have timestamps
`dt, 2dt, ..., 1.2 s`.

Explicit time alignment matters. If the first post-step state is mislabeled as
`t = 0`, every reported rise and settling time is shifted by one sample.

Repeating a constant target before every step also makes the action cadence
visible. The target may persist internally, but an explicit loop has the same
shape later lessons will use when the target changes over time:

```python
q_history = [read_q()]
for _ in range(n_steps):
    franka.control_dofs_position(q_target, all_dofs)
    scene.step()
    q_history.append(read_q())
    qdot_history.append(read_qdot())
    control_history.append(read_control_force())
```

## A bounded PD mental model

### Position error and velocity damping

For a selected revolute DOF with zero target velocity, use this simplified
model:

```text
tau_control ≈ KP × (q_target - q) - KV × qdot
```

For a prismatic DOF the same structure applies, but the output is force rather
than torque. KP supplies an effort proportional to position error. KV opposes
motion and acts as velocity damping.

This equation is a reasoning aid for local response, not the complete Franka
dynamics. It helps form testable predictions:

- increasing KP can correct a given position error more aggressively;
- increasing KP without enough damping can increase speed or overshoot;
- increasing KV can reduce speed and overshoot; and
- too much damping can slow the response.

Each statement says “can,” not “must.” Force clipping, coupling, gravity, the
starting pose, and discrete integration can change the observed relationship.

### Ideal critical damping and its boundary

For an ideal linear, uncoupled, single-DOF system with a constant effective
inertia `I_eff`, the error dynamics can be approximated as:

```text
I_eff × error_ddot + KV × error_dot + KP × error = 0
```

Its damping ratio is:

```text
zeta = KV / (2 × sqrt(KP × I_eff))
```

In that ideal model, `zeta = 1` is critical damping, `zeta < 1` is
underdamped, and `zeta > 1` is overdamped.

The formula explains why KV should be reconsidered when KP changes: keeping KV
fixed while raising KP lowers the idealized damping ratio. It does not prove
that a numeric KP/KV pair is critically damped on Franka. The robot has:

- configuration-dependent effective inertia;
- dynamic coupling among joints;
- gravity and other model forces;
- discrete-time integration and an outer command cadence;
- joint limits and constraint effects; and
- finite actuator force or torque ranges.

Calling a measured case “critically damped” would require a stronger identified
model and evidence than this lesson provides. Describe the observed transient
instead: for example, “no overshoot was observed within this window.”

### Gravity, load, and finite-window error

Suppose a joint is stationary but must support a nonzero gravity torque. In the
simplified proportional controller, a nonzero position error may be required to
generate that balancing torque:

```text
support torque ≈ KP × steady position error
```

With no integral term or exact gravity feedforward, a small nonzero error can
therefore be physically consistent with the controller. However, the final
sample of a 1.2-second trace is not automatically a steady state. Its error may
also include:

- an unfinished transient;
- residual velocity or oscillation;
- actuator saturation;
- coupling from other joints; or
- discretization effects.

Always inspect final velocity, the tail of the trajectory, and the finite-window
settling rule before attributing all final error to gravity.

## Force ranges and saturation

### The controller is bounded

The project defines explicit lower and upper effort ranges for all nine Franka
DOFs. In the bundled model and course configuration:

| DOFs | Effort range | Unit |
|---|---:|---|
| `joint1`–`joint4` | `[-87, 87]` | N·m |
| `joint5`–`joint7` | `[-12, 12]` | N·m |
| two finger DOFs | `[-100, 100]` | N |

The notebook sets and then reads back those values:

```python
franka.set_dofs_force_range(
    lower=force_lower,
    upper=force_upper,
    dofs_idx_local=all_dofs,
)
measured_lower, measured_upper = franka.get_dofs_force_range(
    dofs_idx_local=all_dofs,
)
```

When the unconstrained PD expression asks for more effort than the configured
range, the control contribution is clipped. Raising KP further then cannot
produce proportionally larger applied control. The response is no longer an
unconstrained ideal second-order comparison.

A useful saturation test for joint4 is:

```text
abs(control_force) >= 0.99 × joint4_force_limit
```

The `0.99` factor is a declared numerical detection threshold, not a new force
limit. Report how many samples or how much time satisfy it. A peak value alone
does not show how long clipping dominated the transient.

### Control force is not total internal force

Genesis provides two similarly named observations:

- `get_dofs_control_force()` returns the internal control contribution computed
  from the position or velocity command;
- `get_dofs_force()` returns the actual internal force experienced by the DOFs
  at the current timestep.

They answer different questions. The first is the relevant signal for checking
whether the commanded controller reached its configured range. The second also
reflects the simulated system's internal dynamics and should not be relabeled as
the PD command.

Record which API produced a plot. A y-axis named merely “torque” loses the
distinction and can lead to a false saturation conclusion.

## Lab design: one robot, two experiments

The companion lab uses a Plane, the built-in Franka MJCF, and an optional
Genesis camera. It does not use the later grasping-scene builder, YCB objects,
inverse kinematics, or external downloads.

The numerical path is CPU-capable and does not require rendering. The optional
camera path answers a visual question about posture; the state and control
arrays answer quantitative questions about the transient.

### Declare the scene before build

The essential scene logic remains visible in the notebook:

```python
scene = gs.Scene(
    sim_options=gs.options.SimOptions(dt=0.01, substeps=2),
    show_viewer=False,
)
scene.add_entity(gs.morphs.Plane())
franka = scene.add_entity(gs.morphs.MJCF(file=FRANKA_MJCF))

if render_enabled:
    camera = scene.add_camera(
        res=(720, 540),
        pos=(1.8, -1.8, 1.4),
        lookat=(0.0, 0.0, 0.55),
        fov=42,
        GUI=False,
    )

scene.build()
```

The camera must be added before `scene.build()`. Changing the backend, render
mode, or build-time topology after `gs.init()` requires a clean kernel restart.

The lab's explicit environment contract is:

- `ROBO_GENESIS_BACKEND=auto` or `cpu` selects the requested compute path;
- `ROBO_GENESIS_RENDER=0` skips camera creation and rendering;
- `ROBO_GENESIS_RENDER=1` requires camera creation and a valid finite RGB array;
- output files go only to `ROBO_GENESIS_OUTPUTS_DIR`.

Render-enabled failure is a failure, not permission to silently substitute a
schematic and still claim Genesis-camera evidence.

## Part A: a baseline joint4 move

### Establish the initial state

The project provides a nine-element starting configuration and baseline gains.
Before sending a target, the lab must:

1. resolve all nine DOFs by name;
2. assert the `q_start`, KP, KV, and force-range shapes;
3. verify `q_start` lies inside every position limit;
4. reset all nine positions with `zero_velocity=True`;
5. read the position and velocity back; and
6. capture the initial camera frame or measured Link positions.

The joint4 target is a positive `0.25 rad` step from the starting value while
all other position targets remain unchanged:

```python
q_target = q_start.copy()
q_target[3] += 0.25

if not np.all((lower <= q_target) & (q_target <= upper)):
    raise ValueError("position target exceeds the model limits")
```

The named mapping establishes that array element 3 is joint4 for this runtime
model. The code does not rely on that fact before resolving and checking it.

### Measure motion instead of assuming it

The loop records:

- joint4 target position in rad;
- measured joint4 position `q(t)` in rad;
- measured joint4 velocity `qdot(t)` in rad/s;
- joint4 control contribution in N·m; and
- initial and final robot posture.

At minimum, the final absolute position error should be smaller than the
initial error, every recorded value should be finite, and the array lengths
should match the declared timestamps. Those checks establish that the robot
moved toward the target. They do not by themselves establish a good transient.

A camera pair makes the model and posture change visible. It cannot reveal a
brief overshoot or the peak control torque between the two frames. Conversely,
a line plot quantifies the response but does not prove that the intended robot
asset was framed correctly. The two forms of evidence are complementary.

## Define the step-response metrics before viewing results

The main comparison uses a positive step from `q0` to `q_target` and a finite
1.2-second observation window. Its metrics are operational definitions for
this experiment.

### Rise time

Rise time is the first sampled time at which the measured joint reaches 90% of
the commanded positive step:

```text
q(t) >= q0 + 0.9 × (q_target - q0)
```

If no sample reaches that threshold, report `not observed`. Do not replace it
with the end of the window.

### Overshoot

For this positive step:

```text
overshoot = max(0, max_t(q(t) - q_target))
```

This one-sided definition would need to be reversed for a negative step. Zero
reported overshoot means none was observed at the outer sample times; it does
not prove a continuous trajectory never crossed the target between samples.

### Finite-window settling time

The settling band is `±0.01 rad`. Settling time is the first sampled time at
which the error enters that band and remains there for every later sample in
the recorded window:

```text
abs(q(t:) - q_target) <= 0.01 rad for the rest of the array
```

If no such suffix exists, report `not observed`. If it does exist, call it
finite-window settling. A 1.2-second record cannot prove infinite-horizon
stability or rule out later disturbance.

### Final error, peak speed, and peak control

The remaining metrics are:

```text
final error  = abs(q_target - q at the final sample)
peak speed   = max(abs(qdot))
peak control = max(abs(control force))
```

Final error describes one endpoint, not the whole response. Peak speed and peak
control must state their units. Peak control must be compared with the model's
joint4 force range, and the full control trace should show whether saturation
was a single sample or a sustained interval.

## Part B: isolate KP and KV

The second experiment runs three cases from the same `q_start`, zero velocity,
joint4 target, `dt`, substeps, duration, force range, seed, and non-joint4 gains.

| Case | joint4 KP | joint4 KV | Controlled comparison |
|---|---:|---:|---|
| G1 · Reference | 3500 | 100 | lower-stiffness reference |
| G2 · Higher KP only | 7000 | 100 | G1→G2 changes only KP |
| G3 · More damping | 7000 | 300 | G2→G3 changes only KV |

These values were selected to make differences visible in this model and pose.
They are not a recommended controller for arbitrary Franka tasks or hardware.

Before looking at the arrays, form two hypotheses:

1. G2 may reach 90% no later than G1, but may have greater speed, overshoot, or
   time at the force limit because KP is higher while KV is unchanged.
2. G3 may reduce peak speed and overshoot relative to G2, but may rise more
   slowly because it adds damping at the same KP.

These are predictions to test, not results to print unconditionally. The
notebook must derive every sentence from the current arrays. If a relationship
does not appear, it should report the actual ordering and inspect saturation,
time alignment, initial-state equality, and the observation window.

### Reset every case completely

Changing gains without resetting state does not produce a controlled
comparison. The second case would inherit position and velocity from the first.
Each case therefore begins with:

```python
franka.set_dofs_position(
    q_start,
    dofs_idx_local=all_dofs,
    zero_velocity=True,
)
```

The lab then applies the case's gain vectors, verifies the target and force
range, records `t = 0`, and runs the same number of outer steps. Code should
compare the case dictionaries field by field and assert that G1→G2 changes only
joint4 KP and G2→G3 changes only joint4 KV.

### Guided interpretation has four evidence blocks

Read the result table and trajectories in this order:

1. **G1→G2 isolates KP.** Compare rise, peak speed, overshoot, and settling,
   while confirming KV and every other input match. State the measured
   direction; do not say higher KP is always better.
2. **G2→G3 isolates KV.** Compare rise, peak speed, overshoot, and settling at
   fixed KP. State whether added damping reduced the measured transient and
   what response-time cost appeared.
3. **Final error has a boundary.** Compare final error together with final
   velocity and settling status. Do not infer transient quality from the final
   number or assign all remaining error to gravity.
4. **Actuator limits bound the model.** Compare each control trace with the
   joint4 limit and report the detected saturated samples or duration. If
   clipping occurred, explicitly say that unconstrained ideal-PD reasoning no
   longer explains the entire response.

This interpretation should be generated from the current result arrays. It
must handle `not observed` rise or settling values and must not embed numbers
copied from another machine or backend.

## Visual and quantitative evidence have different jobs

L04 deliberately retains both Genesis-native images and Matplotlib plots.

| Evidence | Source | Question it can answer | Question it cannot answer alone |
|---|---|---|---|
| Initial/final RGB | Genesis `add_camera` and `camera.render` | Was the Franka scene rendered, and how did the visible posture change? | What were rise time, overshoot, or peak torque? |
| Initial/final state schematic | measured Link positions when render is explicitly disabled | Did measured robot geometry change on a headless path? | Was a Genesis RGB renderer verified? |
| `q(t)` plot | measured DOF positions | Did the target track gradually, overshoot, or remain outside the band? | Was the visual asset/camera correct? |
| `qdot(t)` plot | measured DOF velocities | How fast did the joint move, and was residual motion present? | Which effort produced the motion? |
| control-force plot | `get_dofs_control_force()` plus limit lines | Did the controller reach the configured effort range? | What was the total internal force? |
| dynamic metric table | current arrays and declared definitions | How do the controlled cases compare within the window? | Will the relationship hold for every pose and robot? |

When `ROBO_GENESIS_RENDER=1`, both RGB frames must be non-empty finite arrays
with an expected channel shape. A rendering error stops that path. When
`ROBO_GENESIS_RENDER=0`, the notebook prints an explicit render `SKIP` and may
draw the measured-link schematic, whose title must say that it is not a camera
frame.

The source exercise contains initial and final images rather than a video. L04
keeps that evidence form: the short transient is measured more precisely by the
time-series plots, so no video is required.

## Companion notebook workflow

The executable lab follows this order so that every result can be traced back
to its configuration:

1. print lesson metadata, Genesis version, requested and actual backend,
   render mode, seed, and output directory;
2. call `gs.init()` once, declare the Plane, Franka, and optional camera, then
   call `scene.build()`;
3. inspect Links and Joints, resolve the nine named local DOFs, and print a
   name/type/index/unit/limit table;
4. validate all configuration shapes, position limits, effort ranges, and
   finite values;
5. run the baseline joint4 step and preserve the initial sample;
6. display the initial/final posture evidence and plot `q`, `qdot`, and control
   force with units and limit lines;
7. run G1–G3 from identical reset states and verify the one-factor changes;
8. calculate metrics and generate the four-part interpretation from the
   measured arrays; and
9. execute final checks that either print `L04 CHECK: PASSED` or name the exact
   failed invariant.

The minimal CPU path uses `ROBO_GENESIS_RENDER=0` and still executes every
model, control, and metric check. It must label camera work as skipped. The
render-enabled path adds scene evidence but cannot replace the numerical path.

## How to know the lab worked

A successful execution provides all of the following evidence:

- the actual runtime reports the expected named mapping of seven arm and two
  finger DOFs;
- `q_start`, target, gains, limits, and force ranges have the expected shape,
  units, and finite values;
- joint4's target lies within its runtime position limits;
- the baseline's final error is smaller than its initial error;
- timestamps align with the initial sample and every outer step;
- G1, G2, and G3 start from the same position and zero velocity;
- automatic checks confirm the intended one-factor gain changes;
- rise or settling that does not occur is reported as `not observed`;
- the position, velocity, and control-force arrays are finite and plotted with
  units;
- saturation is checked against the read-back force range; and
- the output states whether posture evidence came from Genesis RGB or from an
  explicitly labeled measured-state fallback.

Small numeric differences across supported backends are not automatically a
failure. Preserve the complete arrays and compare the defined relationships.
If the qualitative ordering changes, keep both results and diagnose the cause
instead of hiding one backend.

## Common warnings and failures

### Importer warnings appear during build

With Genesis 1.3.3, importing this MJCF may report version-specific warnings
about tendon approximation, neutral `qpos`, constraint time constants, or
neutral-pose self-collision filtering. Preserve them. A known importer warning
does not by itself prove the run failed, and suppressing all warnings would
erase useful context.

After build, still require the named structure, valid shapes, finite state, and
valid limits. An unknown joint name, non-finite trajectory, or failed assertion
is not excused by the presence of an expected warning.

### A joint name cannot be found

Print the names from the runtime `franka.joints` collection and compare them
with the pinned model. Check the Genesis version and model path before editing
indices. Do not replace the missing name with a guessed list position.

### Command length and index length differ

Print both shapes and identify whether the command is arm-only `(7,)` or
whole-robot `(9,)`. Slice values and indices together. Never rely on implicit
broadcasting for a control command.

### A target crosses a joint limit

Read the current lower and upper arrays, identify the named DOF, and reject or
redesign the experiment. Clipping a target silently changes the requested step
and invalidates comparisons with the other cases.

### The measured position immediately equals the target

Check whether the experiment used `set_dofs_position` instead of
`control_dofs_position`, or read state before a dynamic step. A reset is not a
controller response.

### The response oscillates or overshoots

Confirm that every case began from zero velocity, then inspect KP, KV, `dt`,
substeps, the full velocity trace, and the force limit. Do not diagnose “KP too
high” from a final frame alone.

### Higher KP does not make the measured rise faster

Check that only KP changed, timestamps align, and the target is identical.
Then inspect the control trace for saturation. Once both cases are clipped at
the same limit, doubling KP does not double the available torque.

### The final error is nonzero

Inspect final velocity, the tail of `q(t)`, settling status, gravity loading,
and saturation. Increase the observation window for diagnosis before changing
several controller parameters at once.

### Settling is not observed

Report exactly that. Confirm the `±0.01 rad` band and the suffix rule, then
inspect whether the trace remains outside the band, re-exits it, or simply ends
too soon. Do not format a missing value as a successful time.

### Control force and internal force disagree

Verify which getter produced each array. They are different quantities by API
design. Use `get_dofs_control_force()` for the controller-limit analysis and
label `get_dofs_force()` separately if you inspect it.

### A requested AMD run reports CPU

Record the requested and actual backend. A run is evidence only for the backend
Genesis actually selected. Do not relabel CPU output as an AMD result.

### Rendering fails

If rendering was requested, preserve the error and fail that path. Check that
the camera was declared before build and that the process has the required
graphics environment. If rendering was intentionally disabled, print `SKIP`
and use only the clearly labeled state-derived posture view.

### A build-time setting changed without a restart

`gs.init()` is process-wide, and camera topology is fixed at build. Restart the
kernel before changing backend, render mode, or build-time scene content.

### Diagnostic order

Use the same order each time:

```text
version, requested/actual backend, and render mode
  → model path and build boundary
  → joint names, local DOFs, types, units, and limits
  → command/index shapes and target validity
  → identical reset state and zero velocity
  → q/qdot/control-force finiteness and timestamps
  → force saturation and finite observation window
  → backend comparison or gain adjustment
```

This order finds structural mistakes before they are misdiagnosed as controller
tuning problems.

## Checkpoints and exercises

### Concept checkpoints

Answer these without looking back at the tables:

1. Does a fixed relationship contribute a DOF? Why?
2. Why does this Franka have seven arm joints but nine controlled dimensions?
3. Why can `n_qs` differ from `n_dofs` for a free or spherical joint?
4. What makes `dofs_idx_local` safer than copying a bare integer from another
   model?
5. What units belong to arm position, finger position, arm effort, and finger
   effort?
6. Why is `set_dofs_position(..., zero_velocity=True)` appropriate before an
   experiment but not proof of dynamic control?
7. In the ideal single-DOF model, why should KV be reconsidered after raising
   KP?
8. Why can a nonzero final error be consistent with gravity, yet still not
   prove that gravity caused the entire error?
9. Which getter should be used to test whether the position controller reached
   its configured force range?
10. Why can two camera frames not establish rise time or overshoot?

### Hands-on exercise

Run the baseline and G1–G3 comparison. Before execution, write down the expected
direction of change for rise, overshoot, peak speed, and saturation. Afterward:

1. prove from the printed case configurations that G1→G2 changes only joint4
   KP and G2→G3 changes only joint4 KV;
2. report every metric with units, using `not observed` when required;
3. identify which cases, if any, reached the read-back joint4 force limit and
   for how many samples;
4. explain the measured KP and KV relationships without using the words
   “always” or “universally”;
5. explain why final error alone would have hidden part of the transient; and
6. state the Genesis version, backend, pose, target, timestep, force range, and
   observation window that bound your conclusion.

As an extension, keep G2 unchanged except for doubling the observation window.
Predict which metrics can change merely because more of the trajectory is
observed. Rise time and an already observed peak may remain unchanged, while
finite-window settling status and final error may change. This exercise changes
the evidence window, not the physical controller.

Do not add an arbitrarily higher-gain case. The point is to interpret a
controlled, actuator-limited experiment, not to search for the most violent
motion.

## Summary and connections

- An MJCF file declares the articulated model; build turns it into runtime
  state owned by a rigid Entity.
- Links are rigid bodies, Joints constrain relative motion, DOFs count
  independent motion axes, and `qpos` stores configuration coordinates.
- The fixed-base Franka used here has seven revolute arm DOFs and two prismatic
  finger DOFs. Its equality `n_qs == n_dofs == 9` is model-specific.
- Resolve entity-local DOF indices by joint name, then verify shape, unit, and
  position limit before sending a command.
- `set_dofs_position` resets state; `control_dofs_position` sets a target that
  acts through controller effort and dynamics over `scene.step()`.
- The simplified PD model explains the roles of KP and KV, but effective
  inertia, coupling, gravity, discrete time, constraints, and effort limits
  bound that explanation.
- Read `q(t)`, `qdot(t)`, control force, saturation, and finite-window metrics
  together. A final value or posture image is not the whole transient.
- Genesis camera frames provide scene and posture evidence; measured-state
  plots provide quantitative control evidence. Neither substitutes for the
  other.

L05 will use inverse kinematics to compute arm-joint targets from a desired
end-effector pose and will treat cameras as sensors rather than only scene
evidence. The target still needs the L04 control loop to become motion. L06 will
place this controlled robot into the grasping scene. L07 will sequence the same
joint-control interface into a scripted expert and must continue to respect
limits, timing, and measured state.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned state, gain, position/velocity/force control, force-range,
  and force-observation API semantics.
- [Genesis 1.3.3 `RigidJoint` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_joint.py)
  — version-pinned `n_qs`, `n_dofs`, joint type, and entity-local index
  properties.
- [Genesis 1.3.3 bundled Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — joint types, ranges, actuator parameters, tendon, and equality definitions
  used by this lesson.
- [Genesis 1.3.3 robot-control tutorial](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/examples/tutorials/control_your_robot.py)
  — official position, velocity, and force-control examples.
- [MuJoCo Modeling documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)
  — the MJCF modeling concepts behind bodies, joints, actuators, and
  constraints.
- [Feedback Systems, Åström and Murray](https://fbsbook.org/)
  — open textbook background for second-order response and feedback-control
  reasoning; the idealized damping relation in this lecture is deliberately
  bounded before applying it to the coupled robot.
