# L08 · The Scripted Pick-and-Place Expert

> **Part 2 of L08:** this page turns the source-selection decision into one
> executable banana-to-bowl expert. Return to
> [Demonstration Acquisition Methods](./l08-demonstration-acquisition-methods.md)
> or the [lesson overview](./l08-demonstration-acquisition-and-scripted-experts.md).

## From task intent to an executable rollout

“Put the banana in the bowl” is a task description, not yet a robot command.
The expert has to connect several levels:

```text
task: banana → bowl
  → grasp profile: orientation, height, closing force
  → phase target: hand pose and gripper intent
  → motion primitive: plan, descend, hold, interpolate
  → per-step command and measured state
  → final containment result
```

The implementation source of truth is `robo_genesis.grasp_demo`. The lecture
exposes its state machine and equations so that calling `run_pick_place()` in
the notebook is not a black box, while avoiding a second copy of the full
controller implementation.

## Two small objects define the task contract

### `TaskSpec`: what should happen?

The task identifies the object to pick, the placement target, and a horizontal
tolerance:

```python
from robo_genesis.grasp_demo import TaskSpec

task = TaskSpec(
    pick_object="011_banana",
    place_target="024_bowl",
    success_tol=0.06,
)
```

`place_target` can also be a tabletop `(x, y)` coordinate, but the core lesson
uses the bowl. A named container lets the expert read the bowl's current pose
and lets the outcome check use its current AABB.

### `GraspProfile`: how should this object be grasped?

A task says *which* object; a grasp profile says how the gripper should meet
that object's geometry:

```python
from robo_genesis.grasp_demo import GraspProfile
from robo_genesis.scene_config import TABLE_TOP_Z

banana_profile = GraspProfile(
    yaw_offset=90.0,
    grasp_hand_z=TABLE_TOP_Z + 0.105,
    close_force=-10.0,
    center_align=False,
)
```

The banana profile uses a 90-degree yaw offset, a tuned fixed hand height, and
a closing force of `-10 N`. Near-spherical objects such as the lemon and plum
use `center_align=True`, which derives their grasp height from the settled
object AABB. Profiles make object-specific assumptions visible instead of
hiding them inside phase code.

## The seven-phase expert

The expert first lets the scene settle. Settling prepares the episode and is
not counted as an action phase. It then runs seven ordered phases:

| Phase | Task purpose | Shared primitive | Observable event |
|---|---|---|---|
| 1. pregrasp | Reach a pose above the object with open fingers | IK followed by `plan_path()` | Hand arrives above the grasp point |
| 2. descend | Approach vertically without a lateral sweep | Repeated IK along descending z waypoints | Hand moves down while the object remains on the table |
| 3. grasp | Establish contact and hold the object | Arm position hold plus finger force control | Fingers close and the object can follow the hand |
| 4. lift | Clear the tabletop | Bounded-increment arm targets while maintaining finger force | Object bottom rises above the table |
| 5. transport | Carry the object over the bowl | Bounded-increment arm targets while maintaining finger force | Object xy approaches bowl xy |
| 6. release | Let the object enter the bowl | Arm hold plus open finger-position target | Object separates from the hand |
| 7. retreat | Move the hand away and let the object settle | Direct retreat followed by a short settle | Final object and bowl geometry can be checked |

The order encodes task semantics. Closing before descending would miss the
object. Transporting before lift risks table contact. Checking containment
before release would inspect an object that is still held over the bowl.

## Turn object geometry into a grasp pose

### Top-down orientation

The expert reads the object's settled yaw and adds the profile offset:

```text
grasp_yaw = object_yaw + profile.yaw_offset
grasp_quat = quaternion(roll=180°, pitch=0°, yaw=grasp_yaw)
```

The 180-degree roll points the hand downward. The additional yaw determines
the jaw direction in the tabletop plane. For the elongated banana, the
90-degree offset turns the jaws across its shorter direction rather than along
its length.

L05 already explained world-frame poses, Genesis `wxyz` quaternions, and IK.
Here IK is one component of a task phase: `_ik()` converts each desired hand
pose into a joint candidate, and the chosen motion primitive determines how
that candidate is approached.

### Fixed and geometry-adaptive height

The banana uses a fixed, task-tuned hand-link height. For a near-spherical
object, descending to the same value can put the finger crossbar into the top
of the object. The adaptive profile measures the settled AABB:

```text
center_z      = (z_min + z_max) / 2
half_height   = (z_max - z_min) / 2
fingertip_z   = center_z - drop_fraction × half_height

z_from_jaws  = fingertip_z + hand_to_fingertip
z_from_clear = z_max + palm_clearance

grasp_hand_z = max(z_from_jaws, z_from_clear)
```

The first candidate aims the fingertip midline below the object's centre; the
second keeps the palm and crossbar above the object's top. Taking the higher
candidate satisfies both conditions. The formula adapts one profile family to
settled object height, but it does not replace object-specific validation.

## Match each phase to a motion primitive

### Plan the open-hand approach

Pregrasp is the only phase that calls `plan_path()`. The current Genesis 1.3.3
interface uses `RRTConnect` by default and performs collision checking unless
`ignore_collision=True` is requested. The shared expert leaves collision
checking enabled and executes the returned joint waypoints with the fingers
open.

Planning is appropriate here because the arm may begin far from the object and
the gripper is not yet carrying anything. Once the hand reaches pregrasp, the
remaining approach has a stronger task constraint: move vertically toward the
known object rather than letting an unconstrained joint-space jump sweep
sideways near it.

### Descend through Cartesian z waypoints

The descend primitive keeps xy and orientation fixed while sampling z from
pregrasp to grasp height. It solves IK again for each target pose and advances
the simulation after each joint command. This makes the intended Cartesian
approach visible in the primitive itself.

The distinction is useful:

```text
one far IK target + immediate command
    may produce a lateral hand sweep during dynamic execution

many fixed-xy, descending-z targets
    express the desired vertical approach explicitly
```

### Hold the arm and force-control the fingers

During grasp and transport, the arm remains position controlled while the two
finger DOFs receive force commands. A position target says where a joint should
go; a force command maintains squeeze after contact prevents the fingers from
reaching a fully closed position.

The signs and limits are implementation-specific. In the current profile,
both fingers receive the negative `close_force` value expected by this Franka
model. The scene builder has already configured actuator force ranges.

For the later learning interface, the expert still records the two finger
components of its nine-dimensional action as an open or closed position
target. This keeps the action representation consistent even though the
low-level execution mode during holding is force control. Execution mode and
recorded action semantics are related, but they are not identical.

### Bound the commanded target increment while carrying

Lift and transport use `_goto_interp()` because the object is already in the
gripper. Let the measured arm start be `q_start`, the IK goal be `q_goal`, and

```text
Δq∞ = max(abs(q_goal - q_start)).
```

The implementation chooses

```text
n = max(MOVE_MIN_STEPS, ceil(Δq∞ / MOVE_MAX_DQ))
```

and commands the linear sequence

```text
q_i = q_start + (q_goal - q_start) × i/n,  i = 1, ..., n.
```

Therefore every adjacent commanded arm target differs by at most
`MOVE_MAX_DQ` in infinity norm. With the current constants,
`MOVE_MAX_DQ = 0.006 rad` and `MOVE_MIN_STEPS = 40`; a short hold follows the
ramp.

This is a command-schedule property. Measured velocity and acceleration still
depend on controller gains, force limits, contact, solver behavior, and the
simulation time step. The notebook will verify the command bound directly and
observe the measured trace rather than importing historical acceleration or
slip numbers from another environment.

## Commanded action and measured state

At each control step the recorder hook receives a nine-value commanded action.
It also reads Franka's current nine-value qpos:

```text
state_t  = measured [arm_q(7), finger_q(2)]
action_t = commanded [arm_target(7), finger_target(2)]
```

The planned L08 notebook keeps these values in memory. A minimal recorder has
one responsibility:

```python
from robo_genesis.course_utils import to_numpy

class TraceRecorder:
    def __init__(self, bundle):
        self.bundle = bundle
        self.states = []
        self.actions = []

    def on_step(self, action):
        state = self.bundle.franka.get_qpos()
        self.states.append(to_numpy(state).reshape(-1))
        self.actions.append(to_numpy(action).reshape(-1))
```

The hook observes state immediately before the corresponding command is sent
and the simulator advances. This is a transition-alignment choice, not yet the
complete dataset schema. L09 will define timestamps, image sampling,
decimation, episode boundaries, and persistent fields.

Equal shapes do not make the arrays equal. Tracking error, contact, actuator
limits, and finite controller response can separate measured qpos from the
requested target. The trace should therefore check matching length, `(T, 9)`
shape, finite values, and a nonzero command/state difference during motion.

## Decide whether the banana reached the bowl

After release, retreat, and settling, `check_success()` evaluates a container
target in two parts.

First, compute horizontal placement from the current object and bowl centres:

```text
horizontal_distance = norm(object_xy - bowl_xy)
allowed_radius = min(task.success_tol, bowl_rim_radius)
within_footprint = horizontal_distance < allowed_radius
```

The bowl rim radius is derived from the smaller horizontal extent of its
current AABB. Second, compare the bottom of the banana AABB with
the top of the bowl AABB:

```text
inside_bowl = object_aabb_bottom_z < bowl_rim_z - rim_margin
```

The rollout succeeds only when both booleans are true:

```text
success = within_footprint and inside_bowl
```

Using the banana's bottom is important because an elongated object can rest
partly inside the bowl while its centre remains above the rim. The two printed
components also make a failure interpretable: the object may miss the opening
horizontally, or it may remain above the rim.

This predicate is the operational task definition for the configured bowl. It
is evaluated after the expert has released the object and allowed it to
settle, so the result answers the lesson's task question directly.

## The companion experiment

The notebook will use one clean kernel and one fixed task:

```python
task = TaskSpec("011_banana", "024_bowl")
success, frames = run_pick_place(
    bundle,
    task,
    save_frames=render_enabled,
    recorder=trace,
)
```

The notebook defaults to `ROBO_GENESIS_RENDER=1`. In this normal learning path,
`run_pick_place()` captures eight world-camera images: the settled start plus
one image after each phase. Learners without a working rendering stack can set
the value to `0`; that explicit fallback builds no camera but still runs the
full rollout, produces the action/state trace and numerical plots, expands both
containment components, and checks the result. The expected image-tag order is:

```text
00_start
01_pregrasp
02_reach
03_grasp
04_lift
05_above_target
06_release
07_done
```

The montage should make the phase sequence visually legible. Numerical trace
and containment checks still determine the final notebook result.

## Diagnose the phase that failed

Use the state machine order instead of changing several parameters at once:

1. **Wrong task or profile:** print the object key, target, yaw offset, height
   strategy, and closing force.
2. **Pregrasp does not complete:** inspect the current object pose, desired hand
   pose, IK candidate, and path-planning result.
3. **The object moves during descent:** inspect jaw yaw, AABB-derived grasp
   height, palm clearance, and the intended fixed-xy path.
4. **The object slips during lift or transport:** confirm that finger force is
   maintained and that adjacent commanded arm targets respect the increment
   bound.
5. **The final result is false:** print `within_footprint` and `inside_bowl`
   separately before changing the task tolerance.

If rendering is unavailable, run the non-rendering numerical branch and label
the visual branch as skipped. A missing image should not be replaced with a
fabricated frame.

## Checkpoints and exercise

### Concept checkpoints

1. What belongs in `TaskSpec`, and what belongs in `GraspProfile`?
2. Why is scene settling outside the seven action phases?
3. Why does the expert use a planned approach but an explicit vertical
   descent near the object?
4. Why can the fingers execute force control while the recorded action still
   contains a closed position target?
5. What property does `MOVE_MAX_DQ` establish about commanded targets?
6. Why are both the horizontal and below-rim conditions needed for the bowl?

### One-variable exercise: change the command increment

Keep the same example `q_start` and `q_goal`, but replace `MOVE_MAX_DQ` with a
candidate value. Before calculating, predict how a smaller value changes:

- `ceil(Δq∞ / max_dq)`;
- the final number of waypoints; and
- the maximum adjacent commanded-target difference.

Then compute the schedule with NumPy and check its endpoints and maximum step.
Do not rerun the full grasp, change controller gains, or claim that a smaller
increment automatically improves task success. The exercise isolates the
command schedule from physical response.

## Summary and connection to L09

- `TaskSpec` defines the object, placement target, and tolerance;
  `GraspProfile` defines object-specific grasp geometry and force.
- The expert composes seven readable phases rather than one unexplained action
  sequence.
- Top-down yaw and grasp height connect settled object geometry to an IK target.
- Arm position control, finger force control, and recorded finger targets have
  distinct roles.
- Interpolation bounds adjacent commanded joint targets while lift and
  transport carry the object.
- The in-memory trace keeps commanded action and measured state separate.
- Horizontal footprint plus below-rim depth defines completion for the current
  banana-to-bowl task.

L09 will attach a production recorder to this same per-step hook, choose a
dataset frame rate, align images and state/action samples, define episode
boundaries, and persist only demonstrations that satisfy the task contract.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official engine and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned IK, path-planning, joint-state, and control interfaces.
- Kuffner and LaValle, [“RRT-Connect: An Efficient Approach to Single-Query
  Path Planning”](https://doi.org/10.1109/ROBOT.2000.844730), 2000 — the
  bidirectional planner used by the current Genesis default.
