---
lesson: L07
slug: building-a-grasping-task-scene
locale: en
title: "Building a Grasping Task Scene"
duration_minutes: 90
hardware: cpu-ok
status: planned
---

# L07 · Building a Grasping Task Scene

> **Course status:** the English lecture is complete and under review. The
> Chinese lecture and executable notebooks are still planned, so L07 remains
> `planned`. Scene construction has a complete non-rendering numerical path;
> RGB/depth rendering is a separate capability branch.

## Where this lesson fits

L03 established contact and stable stepping. L04 controlled the Franka joints.
L05 connected joint space to an end-effector pose and introduced a fixed
camera. L06 added an environment dimension. L07 now combines those foundations
into the task world that the rest of the manipulation pipeline will reuse.

The central question is:

> How do project-prepared community assets, configuration geometry, Genesis
> entities, and two camera roles become one testable grasping-task scene?

The lesson follows one chain:

```text
supported open-source assets → project preflight and stable paths
  → table/object/robot/camera configuration
  → build one base scene
  → hold and settle
  → measure robot and object state
  → optionally inspect world/wrist RGB and depth
```

This chain stops before grasp execution. A stable scene is an input to the L08
scripted expert, not evidence that an object can already be picked and placed.
L09 will later define what to record from this scene. L11 will vary selected
scene properties through domain randomization. Neither recording nor
randomization belongs in the L07 experiment.

Before starting, you should be able to:

- explain the `init → declare → build → control → step → read/render`
  lifecycle;
- distinguish static, dynamic rigid, and articulated entities;
- identify Franka's seven arm DOFs and two finger DOFs;
- use a PD position target with repeated `scene.step()` calls;
- interpret world-frame positions, contact with a tabletop, and an
  axis-aligned bounding box (AABB);
- distinguish a fixed camera from a camera attached to a moving link; and
- remember from L06 that a leading environment dimension changes array
  shapes, even though this lesson deliberately returns to one unbatched task
  scene.

### A focused 90-minute route

| Time | Topic | Learner output |
|---:|---|---|
| 0–10 min | Task scene and prepared community assets | Connect the four YCB meshes to their task roles |
| 10–30 min | Configuration and placement geometry | Derive table bounds, rest z, footprints, and separation |
| 30–50 min | Base-scene construction | Build once and inspect the named `SceneBundle` components |
| 50–70 min | Settle and inspect | Check Franka qpos, object positions, AABBs, and drift |
| 70–90 min | World/wrist observations, placement exercise, and L08 handoff | Compare the two views and evaluate one new xy candidate |

Scene lifecycle, entity categories, PD control, and basic camera concepts were
established in L02–L06. This lesson recalls them only where they are needed to
assemble and inspect the task scene.

## Learning objectives

By the end of L07, you should be able to:

1. explain how the table, YCB objects, Franka, and cameras form a reusable
   grasping-task scene for later scripted demonstrations, data collection, and
   policy workflows;
2. use the project-prepared community assets and scene configuration to build
   the base Genesis scene, including suitable mesh collision geometry and
   object placement derived from the table and mesh bounds; and
3. inspect the settled scene and its world/wrist observations to determine
   whether the robot, objects, layout, and cameras are ready for later task
   execution.

## A task scene is a downstream interface

A task scene is more than a picture of a robot beside some objects. It is a
contract consumed by later code. The scripted expert needs named object and
robot handles. A recorder needs stable observation sources. Randomization code
needs explicit configuration boundaries. Evaluation needs the same task
geometry and success-relevant entities.

Four layers keep that contract understandable:

| Layer | Question | Example in L07 |
|---|---|---|
| Asset readiness | Can the project resolve every supported resource? | Four YCB `textured.obj` paths |
| Configuration | What scene should be declared? | Table size, object xy/yaw, home q, camera poses |
| Assembly | How does configuration become Genesis entities? | `build_scene()` adds entities, builds once, and attaches the wrist camera |
| Runtime state | What happened after physics advanced? | Franka qpos, object position/AABB, RGB/depth |

These layers answer different questions. A file can exist while its entity
fails to build. A Scene can build while an object begins below the tabletop. A
camera can return a plausible picture while a numerical state is non-finite.
Conversely, a numerically stable scene can complete its core checks without
creating any camera.

The evidence ladder is therefore:

```text
asset ready
  ≠ entity built
  ≠ state stable after stepping
  ≠ camera observation available
  ≠ scripted grasp successful
```

Never promote a lower rung into a stronger claim.

## Use the prepared community assets

### Run the preflight first

The course repository already contains the four YCB objects used by the task.
Resolve them through the project interfaces:

```python
from robo_genesis.scene_config import get_ycb_assets
from robo_genesis.setup_assets import setup_assets

models_dir = setup_assets()
assets = get_ycb_assets(models_dir)

print(models_dir)
for name, asset in assets.items():
    print(name, asset.mesh_path)
```

The exact keys are:

```text
011_banana
014_lemon
018_plum
024_bowl
```

`setup_assets()` checks that the prepared assets are ready and returns their
models directory. `get_ycb_assets()` then returns one `YCBAsset` record per
supported object, including the mesh path and geometry derived from that mesh.
If the preflight fails, resolve the reported setup problem before building the
scene.

### A mesh has visual and physical responsibilities

The base-scene builder turns each resolved `textured.obj` into a Genesis Mesh
entity. The essential pattern is:

```python
asset = assets[name]
x, y, _ = YCB_LAYOUT[name]["pos"]
z = TABLE_TOP_Z + asset.rest_z_offset

entity = scene.add_entity(
    morph=gs.morphs.Mesh(
        file=str(asset.mesh_path),
        pos=(x, y, z),
        euler=YCB_LAYOUT[name]["euler"],
        align=False,
        convexify=True,
        decimate_face_num=500,
    ),
    material=gs.materials.Rigid(
        rho=300.0,
        friction=YCB_LAYOUT[name].get("friction"),
    ),
)
```

The textured surface tells the renderer what the object looks like. Collision
handling needs geometry suitable for the rigid solver. In this implementation,
`convexify=True` asks Genesis to construct a convex collision approximation
from the supplied mesh, and `decimate_face_num=500` limits its complexity.
That approximation is not the same thing as exact triangle-by-triangle visual
geometry.

This difference matters when interpreting contact. A close-up render may show
a detailed rim or surface indentation that the collision representation only
approximates. L07 checks that objects settle on the tabletop; it does not claim
that every small geometric feature has exact contact behavior.

::: warning Keep asset use reproducible
Use the four project-supported object IDs and the paths returned by
`get_ycb_assets()`. Replacing a mesh, changing its scale, or editing its origin
would change rest height, footprint, collision behavior, and later grasp
parameters. That is a new experiment, not a harmless path fix.
:::

## Compose the grasping scene

### Give every component one explicit role

The base scene contains six kinds of component:

| Component | Genesis representation | Role in this lesson |
|---|---|---|
| Ground | `gs.morphs.Plane()` | Static world reference below the table |
| Tabletop and four legs | Five fixed `gs.morphs.Box` entities | Stable task support with a known top surface |
| Banana, lemon, and plum | Mesh with `gs.materials.Rigid` | Dynamic candidate pick objects |
| Bowl | Mesh with `gs.materials.Rigid` | Dynamic place container for later lessons |
| Franka Panda | Genesis-bundled MJCF | Nine-DOF articulated robot held at home in L07 |
| World and wrist cameras | Fixed camera and hand-attached camera | Global and local observation evidence |

The table is intentionally built from primitives. Its physics dimensions are
therefore explicit and cheap to inspect. The YCB objects retain their visual
identity while using Genesis's collision approximation. Franka is articulated,
so its state and controller interface differ from both fixed boxes and free
rigid objects.

The video camera and domain-randomization hooks supported by the shared builder
are not part of the L07 base scene. Video belongs to later evaluation, while
randomization is the subject of L11.

### Declare first, build once, then attach

The lifecycle from earlier lessons still applies, but an attached camera adds
one important boundary:

```text
before build:
  declare Plane, table, YCB entities, Franka, world camera, wrist camera

scene.build():
  instantiate the declared simulation

after build:
  configure Franka controller
  resolve the runtime hand link
  attach the wrist camera to that link
  synchronize the attached camera
```

The wrist camera must be declared before `scene.build()`, like the fixed world
camera. Its attachment needs the hand link's runtime pose, so
`Camera.attach(...)` happens after build. Each later physics step is followed
by `move_to_attach()` through `SceneBundle.update_wrist_cam()`.

Calling `add_camera()` after build violates the declaration boundary. Calling
`attach()` before build asks for runtime link state too early. Omitting the
per-step synchronization leaves the wrist image at an old pose even while the
robot moves.

## Configuration, assembly, and runtime state

The package gives each responsibility a home:

| Responsibility | Current owner | Examples |
|---|---|---|
| Stable project paths | `robo_genesis.paths` | YCB asset directory, output directory |
| Task configuration | `robo_genesis.scene_config` | Table geometry, YCB layout, Franka home q, cameras |
| Asset readiness | `robo_genesis.setup_assets` | Project preflight and models-directory return value |
| Reusable assembly | `robo_genesis.build_scene` | Entity declaration, build, controller setup, camera attachment |
| Runtime measurements | Genesis entity/camera handles | qpos, position, AABB, RGB, depth |

Do not copy the complete builder into a notebook. Two assembly implementations
would drift as soon as a table dimension, camera parameter, or robot setup
changed. Instead, inspect the configuration and derive the important geometry
directly, call the shared builder once, and then inspect the returned runtime
handles.

### `SceneBundle` is the runtime handle map

`build_scene()` returns a `SceneBundle` rather than a bare `Scene`:

```text
bundle.scene       the built Genesis Scene
bundle.table       [tabletop, leg, leg, leg, leg]
bundle.ycb         object ID → dynamic rigid entity
bundle.franka      the articulated Franka entity
bundle.world_cam   fixed camera or None
bundle.wrist_cam   attached camera or None
bundle.video_cam   evaluation camera or None
```

This map avoids fragile entity-order assumptions. Later code can request
`bundle.ycb["014_lemon"]` instead of guessing which unnamed entity index is the
lemon. The same object names will connect scene construction to the L08 expert.

`SceneBundle` does not hide the runtime mechanism. The caller still controls
when to step, when to update the wrist camera, what state to read, and which
evidence constitutes a pass.

## Turn layout into a geometry contract

### Derive the tabletop bounds

The tabletop center is `(0.35, 0.0)` m and its size is
`(1.20, 0.80, 0.05)` m. If `(c_x, c_y)` is its xy center and `(L_x, L_y)`
its planar size, then:

```text
x_min = c_x - L_x / 2 = -0.25 m
x_max = c_x + L_x / 2 =  0.95 m
y_min = c_y - L_y / 2 = -0.40 m
y_max = c_y + L_y / 2 =  0.40 m
```

The tabletop entity is centered at
`TABLE_TOP_Z - thickness / 2`, so its upper surface is exactly:

```text
TABLE_TOP_Z = 0.75 m
```

That named surface height is the reference for initial object placement and
post-settle AABB checks.

### Derive rest z from mesh bounds

An object mesh origin need not lie on its lowest point. Placing every origin at
`z=0.75` could therefore sink some meshes into the table or leave others
floating.

Let the mesh's local axis-aligned lower bound be
`(b_x^min, b_y^min, b_z^min)`. The project derives:

```text
rest_z_offset = -b_z^min
object_origin_z = TABLE_TOP_Z + rest_z_offset
```

With `align=False`, this preserves the mesh's authored origin. The lowest local
z point then starts at the tabletop surface:

```text
object_origin_z + b_z^min = TABLE_TOP_Z
```

This is an initial placement calculation, not proof of stable contact. The
object must still enter the dynamics loop, settle under gravity, and be checked
again in world coordinates.

### Use a conservative planar footprint

Checking only the object center is insufficient: a center can be inside the
table while part of the object extends over an edge. From mesh xy bounds, the
project computes:

```text
width_x  = b_x^max - b_x^min
width_y  = b_y^max - b_y^min
radius_xy = 0.5 * sqrt(width_x² + width_y²)
```

`radius_xy` is half the diagonal of the axis-aligned xy bounding box. Treating
it as a circular radius is conservative under yaw: the actual mesh may occupy
less area, but the circle will not shrink when the object rotates.

For center `(x_i, y_i)` and radius `r_i`, the full conservative footprint lies
on the table only if:

```text
x_min + r_i ≤ x_i ≤ x_max - r_i
y_min + r_i ≤ y_i ≤ y_max - r_i
```

Two footprints are conservatively separated when:

```text
sqrt((x_i - x_j)² + (y_i - y_j)²) > r_i + r_j
```

Define the pairwise margin as the left side minus the right side. A positive
margin passes; zero or a negative value means the conservative circles touch
or overlap.

### Inspect the current base layout

The current configuration derives these approximate values from the prepared
meshes:

| Object | Role | xy (m) | yaw | Origin z (m) | `radius_xy` (m) |
|---|---|---:|---:|---:|---:|
| `011_banana` | Pick object | `(0.31, 0.22)` | `35°` | `0.768660` | `0.104660` |
| `014_lemon` | Pick object | `(0.34, -0.08)` | `0°` | `0.776508` | `0.042389` |
| `018_plum` | Pick object | `(0.44, 0.08)` | `0°` | `0.776520` | `0.038420` |
| `024_bowl` | Place container | `(0.50, -0.10)` | `0°` | `0.777505` | `0.114066` |

All four centers and conservative footprints fit within the tabletop. Their
centers also lie in the course working region:

```text
REACH_X = [0.30, 0.50] m
REACH_Y = [-0.22, 0.28] m
```

The smallest conservative pairwise margin is approximately `0.004790 m`,
between the lemon and bowl. It is positive but small, so an apparently minor
layout edit can create an initial overlap.

::: warning The working region is not a reachability proof
`REACH_X` and `REACH_Y` are course configuration ranges used by later expert
and randomization code. Membership does not prove that every pose at that xy
has a collision-free IK solution. Orientation, height, joint limits,
obstacles, and path geometry still matter.
:::

### Make the checks executable

The companion lab keeps this logic visible before calling the builder:

```python
from itertools import combinations
import numpy as np

from robo_genesis.scene_config import (
    REACH_X,
    REACH_Y,
    TABLE_CENTER,
    TABLE_TOP_SIZE,
    TABLE_TOP_Z,
    YCB_LAYOUT,
    get_ycb_assets,
)
from robo_genesis.setup_assets import setup_assets

assets = get_ycb_assets(setup_assets())

cx, cy = TABLE_CENTER
length_x, width_y, _ = TABLE_TOP_SIZE
table_x = (cx - length_x / 2, cx + length_x / 2)
table_y = (cy - width_y / 2, cy + width_y / 2)

for name, layout in YCB_LAYOUT.items():
    asset = assets[name]
    x, y, _ = layout["pos"]
    r = asset.radius_xy
    origin_z = TABLE_TOP_Z + asset.rest_z_offset

    assert np.isfinite([x, y, r, origin_z]).all()
    assert table_x[0] + r <= x <= table_x[1] - r
    assert table_y[0] + r <= y <= table_y[1] - r
    assert REACH_X[0] <= x <= REACH_X[1]
    assert REACH_Y[0] <= y <= REACH_Y[1]

for left, right in combinations(YCB_LAYOUT, 2):
    left_xy = np.asarray(YCB_LAYOUT[left]["pos"][:2], dtype=float)
    right_xy = np.asarray(YCB_LAYOUT[right]["pos"][:2], dtype=float)
    margin = (
        np.linalg.norm(left_xy - right_xy)
        - assets[left].radius_xy
        - assets[right].radius_xy
    )
    assert margin > 0.0, (left, right, margin)
```

These checks answer three distinct questions: does the object center lie in
the configured working region, does its conservative footprint remain on the
table, and is it conservatively separated from every other object? Do not
collapse them into one Boolean without labels; a failed category suggests a
different correction.

## Build one base scene

After the asset and layout checks pass, call the shared implementation:

```python
from robo_genesis.build_scene import build_scene

bundle = build_scene(
    show_viewer=False,
    n_envs=1,
    add_world_cam=render_enabled,
    add_wrist_cam=render_enabled,
    add_video_cam=False,
    scene_dr=None,
)
```

This call deliberately disables the evaluation video camera and domain
randomization. `build_scene()` remains the one reusable assembly
implementation; the notebook is responsible for explaining configuration and
checking the result.

For this wrapper, `n_envs=1` selects the single-scene teaching path and the
implementation calls `scene.build()` without an `n_envs` argument. Runtime
arrays are therefore unbatched: Franka qpos is `(9,)`, not `(1, 9)`. This is a
wrapper-specific choice. As L06 explained, calling the Genesis API directly as
`scene.build(n_envs=1)` would retain a leading dimension.

Inspect the structure immediately:

```python
from robo_genesis.course_utils import to_numpy

expected_objects = {
    "011_banana",
    "014_lemon",
    "018_plum",
    "024_bowl",
}

q_initial = to_numpy(bundle.franka.get_qpos())

assert len(bundle.table) == 5
assert set(bundle.ycb) == expected_objects
assert q_initial.shape == (9,)
assert np.isfinite(q_initial).all()
assert bundle.video_cam is None
```

Five table entities means one tabletop plus four legs. It does not include the
ground plane. Matching YCB keys proves that the expected handles were returned,
not that their physical state is already stable.

## Hold, settle, and measure

### A built scene still needs time to evolve

The dynamic objects begin at a geometry-derived contact height. Physics must
resolve contact and gravity over time. The Franka also needs an active target
while that happens; setting its initial q once is not the same as continually
holding a position-controller target.

The base experiment snapshots initial object xy, then advances about 60 steps:

```python
from robo_genesis.scene_config import FRANKA_QPOS

home_q = np.asarray(FRANKA_QPOS, dtype=float)
initial_xy = {
    name: to_numpy(entity.get_pos()).reshape(3)[:2].copy()
    for name, entity in bundle.ycb.items()
}

for _ in range(60):
    bundle.franka.control_dofs_position(home_q)
    bundle.scene.step()
    bundle.update_wrist_cam()
```

The wrist update is harmless when no wrist camera exists, because the bundle
method checks for `None`. Keeping it in the loop makes the lifecycle explicit
and prevents the rendered branch from using a stale attached pose.

### Read both origin position and AABB

For each object, read two related but different quantities:

```python
for name, entity in bundle.ycb.items():
    position = to_numpy(entity.get_pos()).reshape(3)
    aabb = to_numpy(entity.get_AABB()).reshape(2, 3)

    bottom_z = aabb[0, 2]
    xy_drift = np.linalg.norm(position[:2] - initial_xy[name])

    assert np.isfinite(position).all()
    assert np.isfinite(aabb).all()
    assert abs(bottom_z - TABLE_TOP_Z) < 0.005
    assert xy_drift < 0.01
```

`position` is the base-link origin in Genesis's user frame. In this unbatched
scene, its xy axes and origin are the scene coordinates used by the layout.
`aabb[0]` and `aabb[1]` are the world-frame minimum and maximum corners of the
current collision AABB. Its bottom is therefore a better support check than
the entity origin z.

The companion experiment uses these finite-window acceptance checks:

| Quantity after about 60 steps | Requirement |
|---|---:|
| Franka qpos | finite shape `(9,)` |
| Maximum absolute home-q error | `<0.02 rad` |
| Each object position | finite shape `(3,)` |
| Each object AABB | finite shape `(2, 3)` |
| `abs(AABB bottom z - TABLE_TOP_Z)` | `<0.005 m` |
| Object xy drift from its initial center | `<0.01 m` |

These thresholds describe this configured base scene over a short settling
window. They are not general guarantees for arbitrary meshes, scales,
friction settings, physics solvers, or long runs.

An AABB close to the table does not prove graspability. It says the current
collision geometry is resting near the expected support surface. It does not
test finger placement, force closure, lifting, collision-free motion, or bowl
containment.

## Observe the scene from world and wrist cameras

### Fixed and attached views answer different questions

The optional render path uses two cameras:

| Camera | Pose ownership | What it helps inspect |
|---|---|---|
| World camera | Fixed world-frame `pos` and `lookat` | Overall table, object, bowl, and robot arrangement |
| Wrist camera | Rigid transform attached to Franka `hand` | Local eye-in-hand view near the gripper |

Both use the course simulation resolution `(1280, 720)` and vertical FOV
`42°`. Genesis camera configuration uses `res=(W, H)`, while returned arrays
place height before width:

```text
RGB:   (720, 1280, 3), uint8
depth: (720, 1280), floating point
```

The world camera is fully specified before build. The wrist camera is declared
before build but receives its hand-link attachment afterward. The current
offset transform positions and orients it relative to the moving hand, not in
the world frame.

Render through the bundle after the settle loop:

```python
frames = bundle.render(rgb=True, depth=True)

world_rgb, world_depth, _, _ = frames["world"]
wrist_rgb, wrist_depth, _, _ = frames["wrist"]

world_rgb = to_numpy(world_rgb)
world_depth = to_numpy(world_depth)
wrist_rgb = to_numpy(wrist_rgb)
wrist_depth = to_numpy(wrist_depth)
```

For each view, check the exact shape, RGB dtype, finite depth, non-empty RGB
variation, and at least one positive depth value. Then inspect the images:

- the world view should make the four objects, table, and Franka arrangement
  recognizable;
- the wrist view should be a local view consistent with attachment to the
  hand; and
- neither image should be blank, all black, visibly corrupted, or obviously
  pointed away from the task.

Array checks cannot decide whether a camera tells the intended visual story,
so human inspection remains necessary. Conversely, a plausible image cannot
replace qpos, pose, AABB, or drift checks.

### Rendering is a capability branch

The companion notebook uses `ROBO_GENESIS_RENDER` to make the choice explicit:

- `ROBO_GENESIS_RENDER=0`: do not create either camera; complete asset,
  layout, build, settle, and state checks; print a camera `SKIP`;
- `ROBO_GENESIS_RENDER=1`: create both cameras before build and require both
  RGB/depth paths to pass.

If rendering was requested and EGL or the renderer fails, that branch fails.
Do not substitute an old screenshot, an empty array, or a Matplotlib sketch
and label it a Genesis render.

The current resolution, FOV, clipping planes, and poses are course simulation
parameters. They are not a calibrated model of an Intel RealSense D435i or any
other physical camera. This lesson does not reproduce lens distortion,
exposure, sensor noise, depth sensing, synchronization, rolling shutter, or
mounting tolerances.

## Companion lab

The companion notebook will expose the geometry and evidence directly while
reusing `build_scene()` for complete assembly. It will not reproduce the
builder or hide the lesson inside one opaque call.

### Predict before running

Write down answers before executing:

1. Why can an object center be inside the tabletop while its footprint is not?
2. Why is `object_origin_z` higher than `TABLE_TOP_Z` for these meshes?
3. Which scene components are fixed, dynamic rigid, or articulated?
4. Why must both cameras be declared before build, but the wrist attachment
   happen after build?
5. What qpos shape should this `build_scene(n_envs=1)` path return?
6. Can a valid world-camera image prove that the objects settled on the table?
7. What additional actions and success checks must L08 add after the scene is
   stable?

### Minimal numerical path

With rendering disabled, the lab still completes the core lesson:

1. report the environment and initialize one supported backend;
2. run `setup_assets()` and resolve exactly four YCB Mesh paths;
3. calculate table bounds, rest z, conservative footprints, and pairwise
   margins from the current configuration;
4. build one non-randomized scene without cameras;
5. confirm five table entities, four named YCB entities, no video camera, and
   finite Franka qpos `(9,)`;
6. hold the home q target for about 60 physics steps;
7. check home-q error, object position/AABB, tabletop support, and xy drift;
8. report a camera `SKIP`; and
9. print `L07 CHECK: PASSED` only if every requested branch passed.

With rendering enabled, the same notebook declares both cameras before build,
synchronizes the wrist camera after every step, validates both RGB/depth pairs,
and displays the two current RGB views side by side. It does not create a video
camera or save a rollout.

No exception is not a pass. The named structure, shapes, finite values,
geometric inequalities, dynamic thresholds, and requested camera branch all
need explicit evidence.

## Common failures and a diagnostic order

### Asset preflight fails

Run `setup_assets()` first and follow its error message. Confirm that the
project's configured asset directory is being used. Do not copy files from a
neighboring source repository or bypass the preflight in notebook code.

### A path works only from one current directory

Remove relative guesses such as `../assets` and any `sys.path` injection. Use
the installed `robo_genesis` package and its path interfaces. Print the
resolved models directory once when diagnosing the problem.

### An object begins above or below the table

Print the mesh lower z bound, `rest_z_offset`, derived origin z, and
`TABLE_TOP_Z`. Confirm that the mesh uses metres and that `align=False` has not
been changed. After stepping, inspect the world-frame AABB bottom rather than
assuming the origin is the contact point.

### Objects overlap after a layout edit

Recompute every pairwise footprint margin, not only the distance to the nearest
center by eye. Also check the full footprint against the table boundary. The
lemon–bowl margin is already the smallest in the base layout.

### The Scene fails during build

Confirm that all entities and requested cameras were declared before the one
build call. Separate normal first-build compilation or collision-processing
messages from an actual exception. Check the first traceback rather than
retrying in the same partially initialized kernel.

### Objects drift or penetrate during settling

Inspect origin z, initial overlap, AABB bottom, collision settings, and finite
state. A render is useful for locating the object, but the numerical AABB and
drift values decide the lab checks.

### Franka droops while the objects settle

Confirm that the builder configured gains and force ranges, and that the loop
calls `control_dofs_position(home_q)` before every `scene.step()`. Do not tune
new gains in L07; L04 owns the controller explanation.

### The wrist view does not follow the hand

Confirm that the camera was attached to the `hand` link after build and that
`bundle.update_wrist_cam()` runs after each step. A valid but stale image can
still have the expected shape.

### Rendering is blank or EGL is unavailable

If rendering was requested, treat this as a failure of the camera capability
path and inspect the graphics environment. If rendering was intentionally
disabled, complete the numerical path and report only the explicit camera
`SKIP`.

### The scene passes, so the grasp is assumed to pass

Return to the evidence ladder. L07 never sends an IK grasp target, closes the
fingers, lifts an object, or checks containment in the bowl. Those mechanisms
and success criteria begin in L08.

Use this diagnostic order:

```text
version, backend, and render mode
  → asset preflight and resolved paths
  → configuration and derived geometry
  → declaration/build boundary
  → bundle structure and unbatched shapes
  → settle loop and finite state
  → object position, AABB, and drift
  → optional camera attachment and arrays
```

## Checkpoints and exercise

### Concept checkpoints

Answer these without looking back:

1. What are the four layers between an asset on disk and a task observation?
2. Why should notebook code use `setup_assets()` and `get_ycb_assets()` rather
   than a relative path or runtime download?
3. How do fixed table boxes, dynamic YCB Mesh entities, and the articulated
   Franka differ?
4. How is `rest_z_offset` derived, and what does it guarantee before stepping?
5. Why is `radius_xy` conservative under yaw, and what does a positive pairwise
   margin mean?
6. Why does working-region membership not prove IK reachability?
7. Why are both object position and AABB useful after settling?
8. What evidence differs between the world camera, wrist camera, and numerical
   state checks?
9. Which claims remain for L08, L09, L11, and L13?

### Hands-on exercise: propose one new banana xy

Choose one new `(x, y)` candidate for `011_banana`. Change no other variable:
keep its yaw, z derivation, mesh, table, other object positions, robot state,
camera settings, and physics options unchanged.

Before running any code, predict whether the candidate passes:

1. center membership in `REACH_X × REACH_Y`;
2. full conservative-footprint containment on the tabletop; and
3. positive separation margin from the lemon, plum, and bowl.

Then run the explicit geometry checks and report every margin with labels. If
the candidate passes, explain why this still does not prove a reachable,
collision-free grasp. Do not edit `scene_config.py`, build a second Genesis
Scene in the same kernel, or execute the L08 grasp sequence; this exercise is
about reasoning over one placement variable.

## Summary and connections

- A reusable task scene is a downstream interface, not merely a convincing
  image.
- Learner code obtains the four supported YCB assets through project preflight
  and stable path interfaces, then passes each textured mesh to Genesis.
- The scene separates fixed support, dynamic objects, an articulated robot,
  and fixed or attached observation sources.
- Configuration data, assembly behavior, and runtime state have different
  owners. `build_scene()` is the single assembly implementation, while
  `SceneBundle` exposes named runtime handles.
- Mesh lower bounds determine initial rest z. A conservative planar radius
  checks table containment and pairwise separation under yaw.
- The course working region is a configuration range, not a proof of arbitrary
  reachability or a collision-free path.
- A short hold-and-settle loop must precede position/AABB evidence. An entity
  origin and the bottom of its world-frame AABB answer different questions.
- The fixed world camera shows global layout; the hand-attached wrist camera
  shows local eye-in-hand context. Both remain optional on the non-rendering
  numerical path, and neither replaces numerical checks.
- A stable base scene does not prove a successful grasp, correct data timing,
  a useful policy, or closed-loop task success.

L08 will consume the same `SceneBundle`, choose one named object, solve a
sequence of motion targets, control the gripper, and define explicit grasp and
place success criteria. The stable names, geometry, state checks, and camera
lifecycle established here are the prerequisites for that scripted expert.

## Sources

- [Genesis World documentation](https://genesis-world.readthedocs.io/en/latest/)
  — official user and API documentation.
- [Genesis World 1.3.3 on PyPI](https://pypi.org/project/genesis-world/1.3.3/)
  — the exact engine version pinned by this course.
- [Genesis 1.3.3 `Scene` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/scene.py)
  — version-pinned scene declaration and build behavior.
- [Genesis 1.3.3 `Mesh` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/options/morphs.py)
  — version-pinned mesh loading, decimation, convexification, and alignment
  options.
- [Genesis 1.3.3 `RigidEntity` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/engine/entities/rigid_entity/rigid_entity.py)
  — version-pinned entity state, AABB, and position-control behavior.
- [Genesis 1.3.3 `Camera` source](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/vis/camera.py)
  — version-pinned camera declaration, attachment, synchronization, and
  rendering behavior.
- [Genesis 1.3.3 bundled Franka MJCF](https://github.com/Genesis-Embodied-AI/genesis-world/blob/v1.3.3/genesis/assets/xml/franka_emika_panda/panda.xml)
  — the robot model used by the base scene.
- [YCB Object and Model Set](https://www.ycbbenchmarks.com/)
  — original project page for the community object collection used here.
- Calli et al., [“Benchmarking in Manipulation Research: Using the
  Yale-CMU-Berkeley Object and Model Set”](https://doi.org/10.1109/MRA.2015.2448951),
  *IEEE Robotics & Automation Magazine*, 2015 — YCB dataset reference.
- [Intel RealSense D435i product documentation](https://www.intelrealsense.com/depth-camera-d435i/)
  — hardware reference for the explicit statement that this course's simple
  simulation camera parameters are not a calibrated sensor reproduction.
